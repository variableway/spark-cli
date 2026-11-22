"""配乐 + 音效 + 混音 + 母带：python3 audio/synth.py      （python3 audio/synth.py --list-fx 列出全部音效名）
输入：project.json 的 music、timeline.json、audio/events.json（镜头里 EV() 登记的音效）、audio/voice_aligned.wav（没有就不混人声）
输出：audio/music.wav  sfx.wav  mix_final.wav（48 kHz 立体声 16-bit）  voice_proc.wav（有配音时）  audio/checks/wave_mix_small.jpg（看声音的唯一方式）

project.json → music（详见 references/audio.md）：
  source    "synth"（默认，代码合成）| "file"（用户给的歌，须同时给 file）| "none"（只有音效）
  style     source=synth 时："electronic" | "ambient" | "piano"。不写：timeline.mode 为 voice 用 piano，其余用 electronic
  key / progression / chord_beats   "A minor"；["Am","F","C","G"]；每个和弦几拍（默认 4）   （piano 只读 key）
  sections  [{from, to, type}]  拍号相对 timeline.offset；type: intro groove build gap drop break outro   （见 score_electronic.py）
  kicks     [[起拍, 止拍, 步长=1]]  底鼓只放在这些拍上，画面的随拍缩放（kick_zoom）读同一份，所以两边一定一致
  lufs      整体响度目标：有配音 -16，无配音 -14（source=none 只有音效时 -18），true peak ≤ -1 dBTP
  file / start(秒) / gain(dB) / fade_in / fade_out   source=file 时的歌曲路径（相对项目根）、从歌的第几秒开始取（默认 0）、增益；fade_out 对配乐生效
                                      project.json 里 "loop": true 时，配乐尾部 50 ms 与开头交叉淡化，首尾接得上
  piano 的 roles / heartbeat / quiet / insights / minor_span 见 score_piano.py
"""
import json, math, os, re, subprocess, sys, time
from collections import Counter
from types import SimpleNamespace
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import butter, sosfilt
from scipy.ndimage import minimum_filter1d, uniform_filter1d

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import instruments as I
if '--list-fx' in sys.argv: I.list_fx(); sys.exit(0)
import score_electronic, score_piano, checks

ROOT = os.path.dirname(HERE)
CFG = json.load(open(ROOT + '/project.json', encoding='utf-8')); MU = CFG.get('music', {})
TL = json.load(open(ROOT + '/timeline.json', encoding='utf-8'))
SR = 48000; TOTAL = TL['total']; N = int(round(TOTAL * SR)); T0 = time.time()
def log(*a): print(f'[{time.time() - T0:5.1f}s]', *a, flush=True)
def w(path, x): wavfile.write(path, SR, (np.clip(x.T, -1, 1) * 32767).astype(np.int16))
EVS = json.load(open(ROOT + '/audio/events.json', encoding='utf-8')) if os.path.exists(ROOT + '/audio/events.json') else []
I.check_events(EVS)                                                                # 音效名写错：马上报错并列出全部有效名字

source = MU.get('source', 'synth')
if source not in ('synth', 'file', 'none'): sys.exit(f'music.source 只能是 synth / file / none，现在是 {source!r}')
style = MU.get('style') or ('piano' if TL['mode'] == 'voice' else 'electronic')
if source == 'synth' and style not in ('electronic', 'ambient', 'piano'): sys.exit(f'music.style 只能是 electronic / ambient / piano，现在是 {style!r}')
seed = CFG.get('seed', 20261008); rng = np.random.default_rng(seed); I.init(SR, rng)
kicks = []                                                                          # 与 web/core.js 的 KICKS 同一个展开方式
for a, c, *st in MU.get('kicks', []):
    i = a
    while i < c: kicks.append(i); i += (st[0] if st else 1)
BEAT = TL.get('beat') or 60 / TL['bpm']
E = SimpleNamespace(N=N, TOTAL=TOTAL, BEAT=BEAT, BAR=4 * BEAT, OFFSET=TL.get('offset', 0.0), MU=MU, TL=TL, rng=rng, seed=seed, style=style, kicks=sorted(kicks))
has_voice = os.path.exists(ROOT + '/audio/voice_aligned.wav')
os.makedirs(ROOT + '/audio/checks', exist_ok=True)

# ---------------------------------------------------------------- 配乐
if source == 'synth':
    log(f'配乐：{style}', f'（{len(E.kicks)} 个底鼓）' if style != 'piano' else '')
    sc = (score_piano if style == 'piano' else score_electronic).render(E)
    stems, ctx, secs, kick_t = sc['stems'], sc['ctx'], sc['sections'], sc['kicks']
else:
    ctx = score_electronic.harmony(E)[4]; secs = [(s['t0'], s['t1'], s['type']) for s in score_electronic.norm_sections(E, score_electronic.TABLE)] if MU.get('sections') else []
    kick_t = [E.OFFSET + k * BEAT for k in E.kicks]
    if source == 'file':
        import imageio_ffmpeg
        fp = MU.get('file') or sys.exit('music.source 是 file，需要同时写 music.file（歌曲路径，相对项目根）')
        fp = fp if os.path.isabs(fp) else os.path.join(ROOT, fp)
        if not os.path.exists(fp): sys.exit(f'找不到歌曲文件：{fp}')
        raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', fp, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
        song = np.frombuffer(raw, np.float32).reshape(-1, 2).T.astype(np.float64) * 10 ** (MU.get('gain', 0) / 20)
        st = float(MU.get('start', 0)); full = song.shape[1] / SR
        if st:
            if not 0 <= st < full - 0.5: sys.exit(f'music.start = {st:g}s 超出歌曲范围（歌曲 {full:.2f}s）')
            song = song[:, int(round(st * SR)):]
        dur = song.shape[1] / SR; if_start = f'（从歌的 {st:g}s 开始取）' if st else ''
        if dur < TOTAL - 0.05: log(f'!! 歌曲{if_start} {dur:.2f}s，比成片短 {TOTAL - dur:.2f}s：最后 {TOTAL - dur:.2f}s 没有配乐，换一首或缩短成片'); song = np.pad(song, ((0, 0), (0, N - song.shape[1])))
        elif dur > TOTAL + 0.05: log(f'歌曲{if_start} {dur:.2f}s，比成片长 {dur - TOTAL:.2f}s：' + ('循环片，尾部与开头交叉淡化' if CFG.get('loop') else f'片尾 {MU.get("fade_out", 1.5):g}s 内淡出'))
        stems = {'music': song[:, :N]}
        if CFG.get('loop'):                                                     # 循环片：成片首尾相接，音乐也要接得上。把歌里「片尾之后」的 50 ms 与开头交叉淡化，不够长就用片尾自己的最后 50 ms
            X = int(0.05 * SR); m = stems['music']
            tail = song[:, N:N + X] if song.shape[1] >= N + X else None
            if tail is not None:
                ramp = np.linspace(0, 1, X); m[:, :X] = m[:, :X] * ramp + tail * (1 - ramp)       # 开头 50 ms 渐入的是「歌里本来接在片尾后面的声音」，首尾连续
                log('循环片：开头 50 ms 与歌里片尾之后的 50 ms 交叉淡化')
            else:
                ramp = np.linspace(0, 1, X); m[:, :X] = m[:, :X] * ramp + m[:, -X:] * (1 - ramp)
                log('循环片：歌曲后面没有多余的 50 ms，用片尾自己的最后 50 ms 与开头交叉淡化')
    else: stems = {}
    if not stems: stems = {'music': np.zeros((2, N))}
log('配乐完成')

# ---------------------------------------------------------------- 音效：EV 的 t 是动作发生的那一刻；每个音效按注册时的对齐方式（起点 / 峰值 / 结尾）自动提前起点
sfx, srev = I.Bus('sfx', N), I.Bus('srev', N); used = Counter()
for e in EVS:
    if not 0 <= e['t'] < TOTAL: log(f"!! 音效 {e['type']} 的时刻 {e['t']}s 不在片内，已跳过"); continue
    y, g, pan, send, ld = I.fx(e, ctx); sfx.add(e['t'] - ld, y, g, pan); srev.add(e['t'] - ld, y, g * send, pan); used[e['type']] += 1
X = sfx.st() + 0.8 * I.reverb(srev, 1.6, 12, 6500) if used else np.zeros((2, N))
log('音效', sum(used.values()), '个')

# ---------------------------------------------------------------- 人声（有 voice_aligned.wav 才有）：压缩 + 提清晰度 + 说话时压低配乐
def rms_db(x, mask=None):
    x = x if x.ndim == 1 else x.mean(0)
    if mask is not None: x = x[mask > 0.5]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12) if x.size else -120.0
V = np.zeros((2, N)); act = np.zeros(N)
if has_voice:
    from scipy.signal import fftconvolve
    sr_, v = wavfile.read(ROOT + '/audio/voice_aligned.wav'); assert sr_ == SR, '人声采样率必须是 48000'
    v = v.astype(np.float64) / 32768; v = v[:N] if len(v) >= N else np.pad(v, (0, N - len(v)))
    v = I.hp(v, 85, 2); v = v + 0.22 * I.bp(v, 2400, 4800, 1) - 0.12 * I.bp(v, 180, 320, 1)            # 3kHz 提清晰度，250Hz 收闷
    env = np.sqrt(uniform_filter1d(v ** 2, int(0.012 * SR)) + 1e-12); edb = 20 * np.log10(env)
    gr = np.minimum(0, (-24 - edb) * (1 - 1 / 3)); gr = sosfilt(butter(1, 8, 'low', fs=SR, output='sos'), gr); v = v * 10 ** (gr / 20)   # 3:1 压缩
    hv_ = I.ir(0.45, 13, 4500, 0.006); V = np.stack([v + 0.07 * fftconvolve(v, hv_[0])[:N], v + 0.07 * fftconvolve(v, hv_[1])[:N]])
    venv = np.sqrt(uniform_filter1d(v ** 2, int(0.05 * SR)) + 1e-12); active = (20 * np.log10(venv) > -42).astype(np.float64)
    act = 1 - minimum_filter1d(1 - active, int(0.35 * SR)); act = uniform_filter1d(act, int(0.08 * SR))             # 起得快（80ms）落得慢（450ms）
    duck_db = -9 * sosfilt(butter(1, 1.2, 'low', fs=SR, output='sos'), act); duck_db = np.minimum(duck_db, -9 * act)
    stems = {k: x * 10 ** (duck_db / 20) for k, x in stems.items()}; X = X * 10 ** (duck_db * 0.25 / 20)
    log('人声处理完成')
else: log('没有 voice_aligned.wav：只混配乐和音效')

# ---------------------------------------------------------------- 电平关系（母带前，最后统一校响度）
M = sum(stems.values()); xmask = (np.abs(X).mean(0) > 1e-4).astype(float); speech = act > 0.5
if speech.any():
    V *= 10 ** ((-19.0 - rms_db(V, speech)) / 20)
    mg = 10 ** ((-19.0 - (17.0 if style == 'piano' else 13.0) - rms_db(M, speech)) / 20)                    # 人声段音乐比人声低约 17 dB（电子乐 13 dB）
    xg = 10 ** ((-19.0 - 13.0 - rms_db(X, xmask)) / 20) if xmask.any() else 1.0
else:
    mg = 10 ** ((-24.0 - rms_db(M, (np.abs(M).mean(0) > 1e-4).astype(float))) / 20) if np.abs(M).max() > 1e-6 else 1.0
    xg = 1.0                                          # 无配音：音效保持表里的相对电平（冲击最响、点击轻），不按自身均方归一，稀疏的音效才不会被推得过响
stems = {k: x * mg for k, x in stems.items()}; X = X * xg; M = M * mg
fo = MU.get('fade_out', 0.0 if CFG.get('loop') else 1.4 if style == 'piano' and source == 'synth' else 1.5 if source == 'file' else 1.0); fi = MU.get('fade_in', 0.0 if CFG.get('loop') else 0.15 if style == 'piano' and source == 'synth' else 0.02)
fade = np.ones(N); i0 = max(0, int(round((TOTAL - fo) * SR))); fade[i0:] = np.cos(np.linspace(0, np.pi / 2, N - i0)) ** 2
nfi = int(fi * SR)
if nfi: fade[:nfi] *= np.linspace(0, 1, nfi)
M = M * fade; stems = {k: x * fade for k, x in stems.items()}
mix = V + M + X
if not CFG.get('loop'): mix[:, :48] *= np.linspace(0, 1, 48)                        # 防开头爆音；循环片首尾要接上，不做

# ---------------------------------------------------------------- 母带：限幅、响度校准（ebur128）、true peak
def limit(x, ceil_db):
    """软削波（0.55 以上按 tanh 渐近到天花板，压住底鼓这类尖峰）+ 前瞻 5ms 峰值限制器。返回 (信号, 每采样的有效增益；压缩过的 10ms 窗内取最小)"""
    ceil = 10 ** (ceil_db / 20); thr = 0.55; ax = np.abs(x); y = np.where(ax > thr, np.sign(x) * (thr + (ceil - thr) * np.tanh((ax - thr) / (ceil - thr))), x)
    pk = np.abs(y).max(0); g0 = np.minimum(1, ceil / np.maximum(pk, 1e-9))
    g = minimum_filter1d(g0, int(0.005 * SR) * 2 + 1); g = uniform_filter1d(g, int(0.005 * SR)); g = np.minimum(g, minimum_filter1d(g0, 3))
    y = np.clip(y * g, -0.999, 0.999); eff = np.abs(y).max(0) / np.maximum(np.abs(x).max(0), 1e-9)
    return y, minimum_filter1d(np.where(np.abs(x).max(0) > 0.3, eff, 1.0), int(0.01 * SR))     # 10ms 窗内出现过压缩就算「动作中」
def measure(x):
    import imageio_ffmpeg
    p = ROOT + '/audio/checks/_loud.wav'; w(p, x)
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128=peak=true:framelog=quiet', '-f', 'null', '-'], capture_output=True, text=True).stderr
    os.remove(p); L = re.findall(r'I:\s+(-?[\d.]+) LUFS', r); tp = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r)
    return (float(L[-1]) if L else -70.0), (float(tp[-1]) if tp else -90.0)
target = MU.get('lufs', -16.0 if speech.any() else -18.0 if source == 'none' else -14.0)       # 只有音效时默认 -18：稀疏的音效校到 -14 会被推得过响
gain, ceil_db = 1.0, -1.2
if np.abs(mix).max() < 1e-6: out, g, L, tp = mix, np.ones(N), -70.0, -90.0; log('!! 混音是静音的：没有人声、配乐和音效')
else:
    for it in range(8):
        out, g = limit(mix * gain, ceil_db); L, tp = measure(out)
        if abs(L - target) <= 0.3 and tp <= -1.0: break
        if tp > -1.0: ceil_db -= tp + 1.05
        if abs(L - target) > 0.3: gain *= 10 ** ((target - L) / 20)
lim = (g < 0.841).mean() * 100                                                       # 压缩量超过 1.5 dB 的采样占比（软削波的轻微圆角不算）
w(ROOT + '/audio/mix_final.wav', out); w(ROOT + '/audio/music.wav', M * gain); w(ROOT + '/audio/sfx.wav', X * gain)
if has_voice: w(ROOT + '/audio/voice_proc.wav', V * gain)
log('母带完成')

# ---------------------------------------------------------------- 检查图与报告
st_plot = ({'voice': V} if has_voice else {}) | {k: x for k, x in stems.items() if np.abs(x).max() > 1e-6} | ({'sfx': X} if used else {})
band = checks.draw(ROOT + '/audio/checks/wave_mix_small.jpg', out, {k: x * gain for k, x in st_plot.items()}, TL, E.OFFSET, BEAT, secs, [(e['t'], e['type']) for e in EVS if 0 <= e['t'] < TOTAL], kick_t, not (source == 'synth' and style == 'piano'))
print(f'\n总时长 {N / SR:.2f} s · 48 kHz 立体声 16-bit · 来源 {source}' + (f' / {style}' if source == "synth" else ''))
print(f'响度 {L:.1f} LUFS（目标 {target:g}）· true peak {tp:.1f} dBTP · 限幅/削波动作占比 {lim:.2f}%')
if lim > 1:                                                                         # 限幅集中在哪里：模型据此调开那里同时响的声部
    sh = np.convolve((g < 0.841).astype(float), np.ones(SR // 4) / (SR // 4), 'same'); hot = []
    for i in np.argsort(-sh)[:4000:SR // 8]:
        if sh[i] > 0.2 and all(abs(i / SR - h) > 0.5 for h in hot): hot.append(i / SR)
    # 限幅只集中在一两处（drop 第一拍、最大的冲击）是母带的正常工作，放宽到 2%；分散在很多处说明整体混得太满
    if lim > (2 if len(hot) <= 2 else 1):
        print('  ← 混得太满：减少同时响的音效，或给 section 写更低的 level。限幅集中在：' + '、'.join(f'{h:.2f}s' for h in sorted(hot[:4])))
    else:
        print('  · 限幅只集中在 ' + '、'.join(f'{h:.2f}s' for h in sorted(hot)) + '（最响的一下被压住，正常）')
if abs(L - target) > 0.7: print(f'!! 响度没有校到目标（差 {L - target:+.1f} LU）：限幅器已经顶住，减少瞬态很强的音效再试')
if speech.any(): print('音乐在人声段 %.1f dB，无人声段 %.1f dB；音效 %.1f dB（均为母带前电平）' % (rms_db(M, speech), rms_db(M, ~speech), rms_db(X, xmask)))
if used: print('音效统计：' + ' '.join(f'{k}×{v}' for k, v in used.most_common()))
if band: print(band)
print('检查图：audio/checks/wave_mix_small.jpg')
