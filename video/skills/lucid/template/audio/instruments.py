"""乐器与音效库：全部从零合成（numpy / scipy），不用任何采样。
用法（见 synth.py）：import instruments as I; I.init(SR, rng)；之后用 I.piano / I.supersaw / I.d_kick / ... 与 I.fx(event, ctx)。
  钢琴织体：piano pluck bell kick thud；电子乐：saw supersaw synth_pluck d_kick d_clap d_snare d_hat d_crash rev_cymbal riser_noise sub_drop glass e_bass lead_note。
音效表 FX：每个音效注册名字、说明和可选参数；python3 audio/synth.py --list-fx 打印；EV() 登记了表里没有的名字时 check_events 报错。
fx 里的 chord_hit / swell / stab 等需要和声信息，由 ctx 提供：ctx = {'chord_at': f(t)->(root, notes), 'chords': [(root, notes), ...], 'scale': f(n, base)->midi}。
"""
import math
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 48000
RNG = np.random.default_rng(1)


def init(sr, rng):
    global SR, RNG
    SR, RNG = sr, rng


# ---------------------------------------------------------------- 基础
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def tt(n): return np.arange(n) / SR
def S(t): return int(round(t * SR))
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, f0, f1, o=2): return sosfilt(butter(o, [f0, f1], 'band', fs=SR, output='sos'), x)
def noise(n): return RNG.standard_normal(n)
def adsr(n, a=0.005, r=0.05):
    e = np.ones(n); na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e
def expdec(n, tau): return np.exp(-tt(n) / tau)
def P(*xs):
    """不同长度的信号补零后相加"""
    n = max(len(x) for x in xs); o = np.zeros(n)
    for x in xs: o[:len(x)] += x
    return o

class Bus:
    def __init__(s, name, N): s.name = name; s.N = N; s.L = np.zeros(N + SR * 4); s.R = np.zeros(N + SR * 4)
    def add(s, t, sig, g=1.0, pan=0.0):
        i = S(t)
        if i < 0: sig = sig[-i:]; i = 0
        n = min(len(sig), len(s.L) - i)
        if n <= 0: return
        pan = max(-1, min(1, pan)); a = (pan + 1) * math.pi / 4
        s.L[i:i + n] += sig[:n] * g * math.cos(a); s.R[i:i + n] += sig[:n] * g * math.sin(a)
    def st(s): return np.stack([s.L[:s.N], s.R[:s.N]])

# ---------------------------------------------------------------- 乐器
_PC = {}
def piano(m, dur=0.6, vel=0.6, bright=1.0):
    """加法合成钢琴：带非谐性的泛音、各泛音不同衰减、琴槌噪声、制音器释放"""
    k_ = (round(m, 2), round(dur, 2), round(vel, 2), round(bright, 2))
    if k_ in _PC: return _PC[k_]
    f = mtof(m); tail = 0.35; n = int((dur + tail) * SR); t = tt(n)
    B = 0.00035; base = float(np.clip(3.2 * (261.6 / f) ** 0.6, 0.5, 7))
    yl = np.zeros(n); yr = np.zeros(n)
    for k in range(1, 15):
        fk = k * f * math.sqrt(1 + B * k * k)
        if fk > 14000: break
        amp = (1 / k ** 1.6) * math.exp(-(k - 1) * (0.8 - 0.4 * vel) / bright)
        tau1 = base * 0.32 / (1 + 0.5 * (k - 1)); tau2 = base * 1.6 / (1 + 0.35 * (k - 1))
        env_k = 0.62 * np.exp(-t / tau1) + 0.38 * np.exp(-t / tau2)      # 先快后慢的双段衰减（真钢琴的「余音」）
        nstr = 3 if m > 45 else 2
        for j in range(nstr):   # 三根弦轻微失谐 → 缓慢拍频
            det = (j - (nstr - 1) / 2) * (0.9 + 0.25 * k) / 1200
            ph = RNG.uniform(0, 2 * math.pi); sig = np.sin(2 * math.pi * fk * 2 ** det * t + ph) * env_k * amp / nstr
            if j == 0: yl += sig * 1.2; yr += sig * 0.8
            elif j == nstr - 1: yl += sig * 0.8; yr += sig * 1.2
            else: yl += sig; yr += sig
    y = (yl + yr) / 2
    # 琴体共鸣：几个固定的低中频共振峰，让声音有「木头」的厚度
    body = bp(y, 180, 420, 1) * 0.25 + bp(y, 900, 1800, 1) * 0.12
    y = y + body
    # 毡头琴槌：低频的「噗」+ 极轻的机械声，而不是明亮的敲击
    nh = int(0.03 * SR); th = tt(nh)
    felt = np.sin(2 * math.pi * min(f, 220) * 0.5 * th) * np.exp(-th / 0.008) * 0.12 * vel
    mech = lp(noise(nh), 900) * np.exp(-th / 0.004) * 0.05
    y[:nh] += felt + mech
    y = lp(y, 900 + 2600 * vel * bright, 2)                 # 毡音：随力度变亮，整体偏暗
    y = y + 0.18 * lp(np.concatenate([np.zeros(int(0.0007 * SR)), y[:-int(0.0007 * SR)]]), 3000, 1)  # 极短梳状，模拟琴体反射
    env = np.ones(n); na = int(0.002 * SR); env[:na] = np.linspace(0, 1, na)
    rel = int(dur * SR)
    if rel < n: env[rel:] *= np.exp(-(t[rel:] - t[rel]) / 0.16)
    y *= env * vel / 2.2
    _PC[k_] = y
    return y

def pluck(m, dur=0.4, vel=0.5, bright=1.0):
    f = mtof(m); n = int((dur + 0.1) * SR); t = tt(n); y = np.zeros(n)
    for k in range(1, 9):
        if k * f > 14000: break
        y += (1 / k ** (1.6 / bright)) * np.sin(2 * math.pi * k * f * t) * np.exp(-t * (3 + k * 2.2) / max(dur, 0.1))
    y[:int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return y * vel * 0.5

def bell(f, dur=1.6, vel=0.5):
    n = int(dur * SR); t = tt(n); y = np.zeros(n)
    for r, a, d in [(1, 1, 1.0), (2.756, 0.5, 0.55), (5.404, 0.25, 0.3), (8.93, 0.12, 0.18), (0.5, 0.2, 1.2)]:
        y += a * np.sin(2 * math.pi * f * r * t) * np.exp(-t / (dur * d * 0.45))
    y[:96] *= np.linspace(0, 1, 96)
    return lp(y, 5200, 2) * vel * 0.4

def kick(vel=0.6, soft=True):
    n = int(0.45 * SR); t = tt(n)
    f = 46 + 70 * np.exp(-t / 0.035); ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.16)
    if not soft: y += lp(noise(n), 3000) * np.exp(-t / 0.006) * 0.3
    y[:48] *= np.linspace(0, 1, 48)
    return y * vel

def thud(f0=90, dec=0.12, vel=0.6, nz=0.2):
    n = int(dec * 5 * SR); t = tt(n)
    f = f0 * (1 + 0.8 * np.exp(-t / 0.02)); ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / dec) + nz * lp(noise(n), 1800) * np.exp(-t / 0.015)
    y[:48] *= np.linspace(0, 1, 48)
    return y * vel

def nburst(dur, f0, f1, dec=None, vel=0.4, att=0.003):
    n = int(dur * SR); y = bp(noise(n), f0, f1)
    e = expdec(n, dec) if dec else np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    na = max(1, int(att * SR)); e[:na] *= np.linspace(0, 1, na)
    return y * e * vel

def sweep_noise(dur, fa, fb, vel=0.3, shape='swell', q=0.35):
    """带通中心频率从 fa 扫到 fb 的噪声（分块滤波）"""
    n = int(dur * SR); x = noise(n); out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):
        u = i / max(1, n - 1); fc = fa * (fb / fa) ** u
        lo, hi = max(40, fc * (1 - q)), min(20000, fc * (1 + q))
        seg = x[max(0, i - 512): i + blk]
        ys = bp(seg, lo, hi)[-min(blk, n - i):]
        out[i:i + len(ys)] = ys
    u = np.linspace(0, 1, n)
    if shape == 'swell': e = u ** 2 * (1 - np.clip((u - 0.92) / 0.08, 0, 1))
    elif shape == 'hump': e = np.sin(np.pi * u) ** 1.2
    else: e = (1 - u) ** 2
    return out * e * vel

def tone_glide(f0, f1, dur, vel=0.3, dec=None):
    n = int(dur * SR); u = np.linspace(0, 1, n); f = f0 * (f1 / f0) ** u
    y = np.sin(2 * math.pi * np.cumsum(f) / SR)
    e = np.sin(np.pi * u) ** 0.8 if dec is None else np.exp(-tt(n) / dec)
    e[:96] *= np.linspace(0, 1, 96)
    return y * e * vel

# ---------------------------------------------------------------- 电子乐器（宣传片配乐与音效共用）
def _phase(f, n):
    f = np.broadcast_to(np.asarray(f, float), (n,)); return (RNG.uniform() + np.cumsum(f / SR)) % 1.0, f / SR

def saw(f, n):
    """polyBLEP 抗混叠锯齿波；f 可以是标量，也可以是长度 n 的数组（滑音）"""
    ph, dt = _phase(f, n); y = 2 * ph - 1
    m = ph < dt; x = ph[m] / dt[m]; y[m] -= x + x - x * x - 1
    m = ph > 1 - dt; x = (ph[m] - 1) / dt[m]; y[m] -= x * x + x + x + 1
    return y

def env_adsr(n, a, d, s, r, gate):
    t = tt(n); e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    g = int(gate * SR)
    if g < n: e[g:] = e[g] * np.exp(-(t[g:] - t[g]) / max(r, 1e-4)) if g > 0 else 0
    return e

def supersaw(m, dur, voices=7, spread=0.3, rel=0.25, att=0.006):
    """多把失谐锯齿铺开左右声场（立体声 (2, n)）；m 为 MIDI 音高，spread 为最大失谐（半音）"""
    n = int((dur + rel * 5) * SR); L = np.zeros(n); Rr = np.zeros(n)
    for i in range(voices):
        det = (i - (voices - 1) / 2) / max(1, (voices - 1) / 2) * spread
        y = saw(mtof(m + det), n) * (0.6 if i == voices // 2 else 1.0)
        a = ((i / max(1, voices - 1)) * 1.6 - 0.8 + 1) * math.pi / 4
        L += y * math.cos(a); Rr += y * math.sin(a)
    return np.stack([L, Rr]) * env_adsr(n, att, 0.4, 0.75, rel, dur) / voices

def synth_pluck(m, dur=0.18, bright=1.0, vel=1.0):
    """电子拨弦：双锯齿，滤波开口随音符衰减（琶音、旋律用）"""
    n = int((dur + 0.4) * SR); y = 0.6 * saw(mtof(m), n) + 0.4 * saw(mtof(m + 12.04), n); t = tt(n)
    ef = np.exp(-t / 0.05); out = lp(y, 900 + 3500 * bright, 2) * ef + lp(y, 700 + 900 * bright, 2) * (1 - ef)
    out[:48] *= np.linspace(0, 1, 48)
    return out * np.exp(-t / (dur * 0.9)) * vel

def d_stab(notes, dur=0.22, bright=1.0, vel=1.0):
    """和弦短击（立体声）"""
    n = int((dur + 0.6) * SR); out = np.zeros((2, n))
    for m in notes:
        s_ = supersaw(m, dur, 5, 0.22, 0.09)[:, :n]; out[:, :s_.shape[1]] += s_
    ef = np.exp(-tt(n) / 0.07)
    return np.stack([lp(out[c], 1200 + 5500 * bright, 2) * (0.35 + 0.65 * ef) for c in range(2)]) * vel

def d_kick(vel=1.0, heavy=False, tail=0.3):
    n = int(tail * 4 * SR); t = tt(n)
    f = 50 + 110 * np.exp(-t / 0.035) + 60 * np.exp(-t / 0.005)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tail) * (0.55 + 0.45 * np.exp(-t / 0.08)) * 1.15
    y += lp(noise(n), 3500) * np.exp(-t / 0.0025) * 0.22
    if heavy: y = np.tanh(y * 2.2) / np.tanh(2.2)
    y[:24] *= np.linspace(0, 1, 24)
    return y * vel

def d_clap(vel=1.0):
    n = int(0.5 * SR); t = tt(n); y = np.zeros(n); nz = bp(noise(n), 900, 4200, 2)
    for k, dly in enumerate((0, 0.011, 0.022)):
        i = int(dly * SR); y[i:] += nz[i:] * np.exp(-t[:n - i] / 0.006) * (0.8 + 0.1 * k)
    return (y + bp(noise(n), 1000, 3500, 2) * np.exp(-t / 0.09) * 0.45) * vel

def d_snare(vel=1.0, dec=0.11, tune=0):
    n = int(0.45 * SR); t = tt(n); f = 190 * 2 ** (tune / 12)
    return (bp(noise(n), 1500, 8000, 2) * np.exp(-t / dec) * 0.9 + np.sin(2 * np.pi * f * t) * np.exp(-t / 0.05) * 0.6) * vel

def d_hat(vel=1.0, open_=False):
    n = int((0.35 if open_ else 0.08) * SR)
    return hp(noise(n), 7500, 2) * np.exp(-tt(n) / (0.11 if open_ else 0.022)) * vel

def d_crash(vel=1.0, dur=2.2):
    n = int(dur * SR); t = tt(n)
    return (hp(noise(n), 4000, 2) * np.exp(-t / (dur * 0.33)) + hp(noise(n), 9000, 1) * np.exp(-t / 0.05) * 0.5) * vel

def rev_cymbal(dur):
    n = int(dur * SR); return hp(noise(n), 3500, 2) * np.linspace(0, 1, n) ** 3

def riser_noise(dur, f0=200, f1=1800):
    n = int(dur * SR); u = np.linspace(0, 1, n)
    return lp(sweep_noise(dur, 300, 6000, 0.8, 'swell', 0.4) + 0.25 * saw(f0 * (f1 / f0) ** u, n) * u ** 2, 9000, 1)

def sub_drop(dur=1.4, f0=90, f1=32):
    n = int(dur * SR); t = tt(n); f = f1 + (f0 - f1) * np.exp(-t / 0.25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.4))

def glass(m, vel=1.0, dec=0.5):
    n = int(dec * 4 * SR); t = tt(n); f = mtof(m); y = np.zeros(n)
    for r_, a_, d_ in [(1, 1, 1), (2.76, 0.4, 0.5), (5.4, 0.2, 0.3), (8.9, 0.1, 0.2)]:
        y += a_ * np.sin(2 * np.pi * f * r_ * t) * np.exp(-t / (dec * d_))
    y[:48] *= np.linspace(0, 1, 48)
    return y * vel

def e_bass(m, dur):
    """电子低音：正弦 + 低通锯齿，tanh 加一点谐波"""
    n = int((dur + 0.05) * SR); y = 0.7 * np.sin(2 * np.pi * mtof(m) * tt(n)) + 0.5 * lp(saw(mtof(m), n), 700, 2)
    return np.tanh(y * 1.5) * env_adsr(n, 0.004, 0.2, 0.8, 0.03, dur)

def lead_note(m, dur):
    n = int((dur + 0.3) * SR); y = 0.5 * saw(mtof(m), n) + 0.35 * saw(mtof(m + 0.12), n) + 0.25 * lp(np.sign(np.sin(2 * np.pi * mtof(m - 12) * tt(n))), 6000, 2)
    return hp(lp(y, 2600, 2), 320, 2) * env_adsr(n, 0.004, 0.15, 0.7, 0.08, dur * 0.92)

def filt_auto(x, fc, kind='low', blk=2048):
    """截止频率随时间变化的滤波（x: (2, n)，fc: 长度 n 的 Hz 曲线）。分块滤波并保留滤波器状态，截止频率变化超过 4% 才重算"""
    out = np.empty_like(x); zi = None; last = None; sos = None
    for i in range(0, x.shape[1], blk):
        c = float(np.clip(fc[i], 20, 20000))
        if sos is None or abs(c / last - 1) > 0.04:
            sos = butter(2, c, kind, fs=SR, output='sos'); last = c
            if zi is None: zi = np.zeros((1, 2, 2))
        out[:, i:i + blk], zi = sosfilt(sos, x[:, i:i + blk], axis=-1, zi=zi)
    return out

def ir(dur, seed, lpf=6000, pre=0.012):
    r = np.random.default_rng(seed); n = int(dur * SR); t = tt(n); out = []
    for ch in range(2):
        x = r.standard_normal(n) * np.exp(-t / (dur / 6.9)); x = lp(x, lpf, 1); x[:int(pre * SR)] = 0; out.append(x / np.sqrt((x ** 2).sum()))
    return out

def reverb(bus, dur, seed, lpf):
    """把送混响的总线卷积成立体声混响信号 (2, N)"""
    L, R = bus.st(); h = ir(dur, seed, lpf); N = bus.N
    return np.stack([fftconvolve(L, h[0])[:N], fftconvolve(R, h[1])[:N]])


# ---------------------------------------------------------------- 音效表：EV(t, '名字', {…}) 登记的名字全在这里
# 每个音效 f(e, ctx) → (波形, 增益, 声像, 混响送量)。通用可选参数（对所有音效有效）：v 音量倍数，pan 声像 -1..1，align 覆盖对齐方式。
# EV(t, ...) 的 t 永远是「动作发生的那一刻」。注册时用 at 说明声音的哪一点对准 t，混音时 synth 自动把起点提前：
#   'start' 起点：击打类，瞬态就在开头（点击、落位、冲击）。默认
#   'peak'  峰值：划过类，最响处在中间（whoosh、swish、swoop），最响的那一刻对准 t
#   'end'   结尾：冲向某一刻的类（riser、whoosh_in、rev_crash），声音结束的那一刻对准 t，所以起点在 t - dur 附近
# 这样不同音效登记在同一个 t，听感上落在同一刻；不用按「峰值在起点后 300 毫秒」手动提前。
FX = {}; _GRP = ['']
AT_NAME = {'start': '起点', 'peak': '峰值', 'end': '结尾'}
def group(name): _GRP[0] = name
def fx_(names, doc, opts='', at='start'):
    assert at in AT_NAME, at
    def deco(f):
        for n in names.split(): FX[n] = (f, doc, opts, _GRP[0], at)
        return f
    return deco

def _a(e): return e.get('pan', 0.0), e.get('n', 0), e.get('dur', 0.6)
def _swell(y): return y * np.linspace(0, 1, len(y)) ** 2

def lead(y, at):
    """波形的起点要比登记时刻 t 早多少秒，才能让 at 指定的那一点落在 t。峰值 = 10ms 包络最大值附近 90% 以上那一段的中心（宽的 hump 取中心，不被噪声抖动带偏）；结尾 = 包络最后一次高于峰值 10% 的位置"""
    if at == 'start' or not len(y): return 0.0
    env = uniform_filter1d(np.abs(y), int(0.01 * SR)); m = env.max()
    if m <= 0: return 0.0
    if at == 'end': return float(np.flatnonzero(env >= 0.1 * m)[-1]) / SR
    i0 = int(env.argmax()); lo = np.flatnonzero(env[:i0] < 0.9 * m); hi = np.flatnonzero(env[i0:] < 0.9 * m)
    return ((lo[-1] if len(lo) else 0) + (i0 + hi[0] if len(hi) else len(y))) / 2 / SR

def fx(e, ctx):
    """返回 (波形, 增益, 声像, 混响送量, 提前量秒)：synth 把波形放在 e['t'] - 提前量"""
    r = FX[e['type']][0](e, ctx); return r[0], r[1] * e.get('v', 1.0), r[2], r[3], lead(r[0], e.get('align') or FX[e['type']][4])

def list_fx():
    cur = None; seen = set()
    for n, (f, doc, opts, g, at) in FX.items():
        if (f, doc) in seen: continue
        seen.add((f, doc)); names = ' / '.join(k for k, v in FX.items() if v[0] is f and v[1] == doc)
        if g != cur: cur = g; print(f'\n【{g}】')
        print(f'  {names:22s} 对准{AT_NAME[at]}  {doc}' + (f'  [参数 {opts}]' if opts else ''))
    print('\n对准：EV 的 t 是动作发生的那一刻；起点 = 声音从 t 开始，峰值 = 最响处落在 t，结尾 = 声音结束在 t（t 之前先响一段 dur）。')
    print('通用参数：v 音量倍数（默认 1），pan 声像 -1..1，align 覆盖对齐（start / peak / end）。EV(t, "名字", {dur: 0.8, n: 3})')

def check_events(evs):
    bad = sorted({e['type'] for e in evs if e['type'] not in FX})
    if bad: raise SystemExit(f'未知音效名：{bad}\n有效名字（共 {len(FX)} 个，说明见 python3 audio/synth.py --list-fx）：\n  ' + ' '.join(FX))
    bad = sorted({str(e['align']) for e in evs if e.get('align') not in (None, *AT_NAME)})
    if bad: raise SystemExit(f'align 只能是 start / peak / end，现在是 {bad}')

group('点击与提示')
@fx_('ping ping_far', '清亮的铃音，标记「出现了一个点」；ping_far 更远更暗', 'n 音高序号, harm 叠和声')
def _ping(e, ctx):
    pan, n_, d = _a(e); m = ctx['scale'](n_ % 6, 5); y = P(bell(mtof(m), 0.9, 0.5), 0.3 * bell(mtof(m + 7), 0.6, 0.3))
    if e.get('harm'): y = P(y, 0.6 * bell(mtof(m - 5), 1.0, 0.4), 0.4 * bell(mtof(m + 4), 0.8, 0.3))
    return (lp(y, 2400), 0.35, pan, 0.9) if e['type'] == 'ping_far' else (lp(y, 3800), 0.5, pan, 0.4)
@fx_('tick_soft', '极轻的高音滴答，列表逐项出现', 'pitch')
def _tick_soft(e, ctx): return lp(pluck(86 + 2 * e.get('pitch', 0), 0.1, 0.6, 1.0), 4000), 0.26, e.get('pan', 0.0), 0.3
@fx_('tick', '清脆的玻璃滴答，比 tick_soft 亮，数字跳动、标签出现', 'n 音高序号')
def _tick(e, ctx): return glass(88 + [0, 2, 4, 7, 9][e.get('n', 0) % 5], 0.5, 0.08), 0.16, e.get('pan', 0.0), 0.25
@fx_('tick_drop', '下滑的短滴答，元素落入位置', '')
def _tick_drop(e, ctx): return P(tone_glide(1700, 1000, 0.09, 0.5, 0.03), thud(200, 0.04, 0.3, 0.1)), 0.5, e.get('pan', 0.0), 0.25
@fx_('tick_run', '一串升调滴答，计数、进度条跑动', 'n 个数(默认 8), dur 总时长')
def _tick_run(e, ctx):
    pan, _, d = _a(e); k = int(e.get('n', 8)); out = np.zeros(int((d + 0.2) * SR))
    for i in range(k): y = pluck(84 + i, 0.06, 0.4, 1.6); j = int(i / k * d * SR); out[j:j + len(y)] += y
    return out, 0.35, pan, 0.2
@fx_('click', '短促的点击；clack 是双击（落键、卡扣）', '')
@fx_('clack', '双击音（落键、卡扣）', '')
def _click(e, ctx):
    y = lp(thud(900 if e['type'] == 'click' else 500, 0.012, 0.6, 0.35), 3500)
    if e['type'] == 'clack': y = P(y, np.concatenate([np.zeros(int(0.035 * SR)), thud(320, 0.012, 0.5, 0.5)]))
    return y, 0.5, e.get('pan', 0.0), 0.2
@fx_('blip', 'UI 提示双音，按钮、开关、状态切换', '')
def _blip(e, ctx):
    n = int(0.03 * SR); t = tt(n)
    return P(np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.005) * 0.5, np.sin(2 * np.pi * 3600 * t) * np.exp(-t / 0.004) * 0.25), 0.25, e.get('pan', 0.0) + 0.3, 0.2
@fx_('key type', '键盘敲击声，每次略有不同；打字时每个字符一个', 'n 字符序号(决定音色变化)')
def _key(e, ctx):
    r = np.random.default_rng(int(e['t'] * 1000) + e.get('n', 0)); n = int(0.06 * SR); x = tt(n); k = r.uniform(0.7, 1.0)
    y = (lp(bp(r.standard_normal(n), 900, 4500, 2), 3200, 2) * np.exp(-x / 0.003) * 0.7 + 0.8 * np.sin(2 * np.pi * r.uniform(240, 330) * x) * np.exp(-x / 0.012)
         + 0.3 * thud(r.uniform(140, 180), 0.012, 0.6, 0.1)[:n]) * k
    return y, 0.17, e.get('pan', r.uniform(-0.3, 0.3)), 0.1
@fx_('shutter', '相机快门：两声机械咔嚓，截图、拍照、定格', '')
def _shutter(e, ctx):
    n = int(0.03 * SR); x = tt(n); c1 = P(bp(noise(n), 1500, 8000, 2) * np.exp(-x / 0.004), thud(180, 0.02, 0.6, 0.3)[:n])
    return P(c1, np.concatenate([np.zeros(int(0.07 * SR)), 0.6 * c1])), 0.3, e.get('pan', 0.0), 0.15
@fx_('pop', '气泡弹出，按钮、卡片、徽标出现', 'n 音高序号')
def _pop(e, ctx):
    pan, n_, _ = _a(e); f = mtof(ctx['scale'](n_, 3)); n = int(0.09 * SR); t = tt(n)
    return np.sin(2 * math.pi * np.cumsum(f * (1.6 - 0.6 * np.minimum(1, t / 0.02))) / SR) * np.exp(-t / 0.022), 0.38, pan + 0.15 * ((n_ % 5) - 2), 0.25
@fx_('pin wood node step', '短促的音高点：pin 钉住，wood 木块，node 节点，step 台阶(升调)', 'n 序号')
def _pin(e, ctx):
    pan, n_, _ = _a(e); ty = e['type']
    f = mtof({'pin': 84, 'wood': 76 + [0, 2, 4, 7, 9][n_ % 5], 'node': ctx['scale'](n_, 3), 'step': 78 + 2 * n_}[ty]); n = int(0.18 * SR); t = tt(n)
    y = (np.sin(2 * math.pi * f * t) + 0.4 * np.sin(2 * math.pi * f * 2.71 * t)) * np.exp(-t / 0.035)
    if ty == 'pin': y = P(y, thud(160, 0.05, 0.4, 0.2))
    return y, 0.36, pan, 0.25
@fx_('pluck', '一个拨弦音，随调性取音', 'n 音阶序号')
def _pluck(e, ctx): return pluck(ctx['scale'](e.get('n', 0), 5), 0.35, 0.6, 1.4), 0.45, e.get('pan', 0.0), 0.3
@fx_('glitch', '数字故障短音，画面撕裂、错位', 'n 变化序号')
def _glitch(e, ctx):
    pan, n_, _ = _a(e); n = int(0.07 * SR); t = tt(n); f = 1100 * 2 ** ((n_ % 6) / 6)
    return lp(np.round(np.sign(np.sin(2 * math.pi * f * t)) * np.exp(-t / 0.02) * 6) / 6, 5000), 0.13, pan + 0.2 * ((n_ % 3) - 1), 0.1
@fx_('sparkle', '一串上行的玻璃音，完成、解锁、点亮', 'n 音符数(默认 8), dur 总时长(默认 0.5)')
def _sparkle(e, ctx):
    k = int(e.get('n', 8)); d = e.get('dur', 0.5); out = np.zeros(int((d + 1.2) * SR)); ps = [0, 2, 4, 7, 9]
    for i in range(k):
        y = glass(84 + ps[i % 5] + 12 * (i // 5), 0.4, 0.2); j = int(i / k * d * SR); out[j:j + len(y)] += y[:len(out) - j]
    return out, 0.1, e.get('pan', 0.0), 0.6
@fx_('shimmer', '一束柔和的高音泛光，强调、收尾', '')
def _shimmer(e, ctx):
    out = np.zeros(int(1.6 * SR))
    for i, o in enumerate([0, 2, 4, 7, 9, 12]): y = glass(98 + o, 0.25, 0.3); j = int(i * 0.05 * SR); out[j:j + len(y)] += y[:len(out) - j]
    return out, 0.12, e.get('pan', 0.0), 0.8
@fx_('chime_up', '三音上行钟声，成功、通过', '')
def _chime_up(e, ctx):
    out = np.zeros(int(1.4 * SR))
    for j, m in enumerate([81, 85, 88]): out = P(out, np.concatenate([np.zeros(int(j * 0.09 * SR)), bell(mtof(m), 0.9, 0.45)]))
    return out, 0.45, e.get('pan', 0.0), 0.4
@fx_('gate_ok', '两音确认钟，校验通过', '')
def _gate_ok(e, ctx):
    out = np.zeros(int(0.9 * SR))
    for j, m in enumerate([81, 86]): out = P(out, np.concatenate([np.zeros(int(j * 0.11 * SR)), bell(mtof(m), 0.6, 0.45)]))
    return out, 0.3, e.get('pan', 0.0), 0.3
@fx_('bell', '高处一声长钟，片尾落版', '')
def _bell(e, ctx): return P(bell(mtof(93), 2.2, 0.55), 0.5 * bell(mtof(88), 1.8, 0.4)), 0.42, e.get('pan', 0.0), 0.5

group('冲击与落位')
@fx_('impact', '宣传片主冲击：底鼓 + 次低频下坠 + 镲，只给全片最大的一两个动作', 'size 大小(默认 1，大冲击 1.3)')
def _impact(e, ctx):
    sz = e.get('size', 1.0); n = int(0.5 * SR)
    y = P(d_kick(0.7, True), sub_drop(1.2 * sz, 120, 34) * 0.7, d_crash(0.7, 1.4 + 0.6 * sz), lp(noise(n), 300) * np.exp(-tt(n) / 0.08) * 0.6)
    return y, 0.12 * min(1.25, sz), e.get('pan', 0.0), 0.35
@fx_('boom', '低频轰鸣，比 impact 软，标题、段落转换', 'dur 时长(默认 1.4)')
def _boom(e, ctx): return sub_drop(max(0.8, e.get('dur', 1.4)), 100, 33), 0.2, e.get('pan', 0.0), 0.3
@fx_('logo_hit', '落版冲击：次低频 + 玻璃和弦，品牌标志定格', '')
def _logo_hit(e, ctx):
    n = int(1.6 * SR)
    y = P(sub_drop(1.6, 110, 33), lp(bp(noise(n), 150, 5000), 2500) * np.exp(-tt(n) / 0.05) * 0.45, glass(81, 0.55, 0.9), 0.6 * glass(88, 0.4, 0.7), 0.5 * glass(69, 0.5, 1.1))
    return y, 0.15, e.get('pan', 0.0), 0.4
@fx_('stab', '合成器和弦短击（跟随调性），卡点强调', '')
def _stab(e, ctx):
    root, notes = ctx['chord_at'](e['t'] + 0.01); return d_stab([m + 12 for m in notes[:4]], 0.18, 1.0).mean(0), 0.2, e.get('pan', 0.0), 0.5
@fx_('num_hit', '数字落地的低频重击', 'big 更大更长')
def _num_hit(e, ctx):
    big = e.get('big', 0); return P(thud(55, 0.35 if big else 0.22, 0.9, 0.15), piano(38, 1.2 if big else 0.7, 0.5, 0.5)), 0.5, e.get('pan', 0.0), 0.2
@fx_('stamp', '盖章：厚实的一击加一点高频', '')
def _stamp(e, ctx): return P(thud(75, 0.1, 0.9, 0.5), nburst(0.03, 300, 3000, 0.008, 0.6)), 0.6, e.get('pan', 0.0), 0.2
@fx_('heavy', '沉重的底鼓加钢琴低音', '')
def _heavy(e, ctx): return P(kick(0.9, False), thud(62, 0.18, 0.6, 0.35), 0.8 * piano(38, 1.0, 0.55, 0.5)), 0.6, e.get('pan', 0.0), 0.25
@fx_('thunk', '短促的闷响，元素砸到位', '')
def _thunk(e, ctx): return thud(120, 0.07, 0.8, 0.3), 0.5, e.get('pan', 0.0), 0.15
@fx_('low_hit', '低沉的一击，带钢琴低音尾巴', '')
def _low_hit(e, ctx): return P(thud(49, 0.6, 0.8, 0.05), 0.6 * piano(38, 1.4, 0.45, 0.5)), 0.55, e.get('pan', 0.0), 0.3
@fx_('land', '轻落地声', '')
def _land(e, ctx): return thud(70, 0.15, 0.7, 0.2), 0.45, e.get('pan', 0.0), 0.25
@fx_('car_in', '短闷响，卡片入槽', '')
def _car_in(e, ctx): return thud(95, 0.09, 0.6, 0.3), 0.4, e.get('pan', 0.0), 0.2
@fx_('chord_hit', '钢琴和弦重击，跟随当前和弦', 'chord 和弦序号')
def _chord_hit(e, ctx):
    root, notes = ctx['chord_at'](e['t'] + 0.01) if e.get('chord') is None else ctx['chords'][e['chord'] % len(ctx['chords'])]; out = np.zeros(int(3.6 * SR))
    for j, m in enumerate([root + 12, root + 24] + notes): y = piano(m, 2.6, 0.55 if j < 2 else 0.45, 0.8)[:len(out)]; out[:len(y)] += y
    return P(out, thud(55, 0.08, 0.5, 0)), 0.42, e.get('pan', 0.0), 0.4
@fx_('fall2', '两音下行的钢琴叹息，转折、坏消息', '')
def _fall2(e, ctx): return P(piano(69, 0.4, 0.55), np.concatenate([np.zeros(int(0.32 * SR)), piano(66, 0.9, 0.5)])), 0.65, e.get('pan', 0.0), 0.35
@fx_('wheel', '两下滚轮声', '')
def _wheel(e, ctx):
    y = lp(thud(220, 0.02, 0.5, 0.35), 2500); return P(y, np.concatenate([np.zeros(int(0.075 * SR)), 0.8 * y])), 0.35, e.get('pan', 0.0), 0.15
@fx_('paper', '纸张翻动', '', at='peak')
def _paper(e, ctx):
    pan, n_, _ = _a(e); return nburst(0.22, 1200, 5000, None, 0.5) * (1 + 0.5 * np.sin(2 * math.pi * 38 * tt(int(0.22 * SR)))), 0.22, pan + 0.2 * ((n_ % 3) - 1), 0.15

group('转场与运动')
@fx_('whoosh', '空气划过，镜头移动、元素飞入飞出', 'dur 时长(默认 0.6), rev 反向(用于吸入), soft 更轻', at='peak')
def _whoosh(e, ctx):
    y = sweep_noise(max(0.2, e.get('dur', 0.6)), 300, 3500, 0.7, 'hump', 0.45)
    if e.get('rev'): y = y[::-1]
    return y, 0.2 if e.get('soft') else 0.32, e.get('pan', 0.0), 0.3
@fx_('whip', '又快又尖的划过，硬切、甩镜头', '', at='peak')
def _whip(e, ctx): return sweep_noise(0.18, 700, 7000, 0.8, 'hump', 0.4), 0.3, e.get('pan', 0.0), 0.15
@fx_('swish pen', 'swish 高频轻扫（卡片、文字滑过）；pen 带笔触颗粒的书写声', 'dur 时长', at='peak')
def _swish(e, ctx):
    y = sweep_noise(max(0.25, e.get('dur', 0.6)), 2500, 5200, 0.5, 'hump', 0.4)
    if e['type'] == 'pen': y *= 0.6 + 0.4 * np.abs(np.sin(2 * math.pi * 23 * tt(len(y))))
    return y, 0.3 if e['type'] == 'swish' else 0.38, e.get('pan', 0.0), 0.15
@fx_('whoosh_in', '由弱渐强的气流，元素从远处冲来', 'dur', at='end')
def _whoosh_in(e, ctx): return sweep_noise(max(0.3, e.get('dur', 0.6)), 300, 3500, 0.7, 'swell', 0.45), 0.35, e.get('pan', 0.0), 0.3
@fx_('riser', '上升的噪声加音高，build 里的拉升；t 写它冲向的那一刻（下一个大动作），声音在 t 之前 dur 秒开始', 'dur 时长(默认 1.5)', at='end')
def _riser(e, ctx):
    d = max(0.5, e.get('dur', 1.5)); return P(sweep_noise(d, 400, 7000, 0.6, 'swell'), _swell(tone_glide(220, 880, d, 0.18, 1e9))), 0.3, e.get('pan', 0.0), 0.4
@fx_('downlifter', '下降的噪声加音高，冲击之后的回落、转入安静', 'dur 时长(默认 1.2)')
def _downlifter(e, ctx):
    d = max(0.5, e.get('dur', 1.2)); return P(sweep_noise(d, 6000, 300, 0.6, 'fall', 0.4), tone_glide(880, 110, d, 0.15, 1e9) * np.linspace(1, 0, int(d * SR)) ** 2), 0.28, e.get('pan', 0.0), 0.4
@fx_('rev_crash', '反向镲，冲击前的吸气', 'dur 时长(默认 1.2)', at='end')
def _rev_crash(e, ctx): return rev_cymbal(max(0.4, e.get('dur', 1.2))), 0.12, e.get('pan', 0.0), 0.2
@fx_('swoop boundary wind', '中低频的大幅扫动：swoop 掠过，boundary 越界，wind 风声', 'dur', at='peak')
def _swoop(e, ctx):
    ty = e['type']; dd = max(0.5, e.get('dur', 0.6) if ty != 'boundary' else 0.9)
    return sweep_noise(dd, 400, 1600 if ty != 'wind' else 900, 0.55, 'hump', 0.5), 0.3 if ty == 'wind' else 0.25, e.get('pan', 0.0), 0.4
@fx_('rush', '加速冲刺声', 'dur', at='end')
def _rush(e, ctx):
    d = max(0.4, e.get('dur', 0.6)); return P(lp(sweep_noise(d, 400, 3200, 0.6, 'swell'), 4000), tone_glide(220, 660, d, 0.15)), 0.2, e.get('pan', 0.0), 0.3
@fx_('rise', '单音上滑加噪声', 'dur', at='end')
def _rise(e, ctx):
    d = max(0.4, e.get('dur', 0.6)); return P(tone_glide(300, 900, d, 0.4), sweep_noise(d, 500, 3000, 0.4, 'swell')), 0.3, e.get('pan', 0.0), 0.4
@fx_('slide slide_down', 'slide 滑动沙沙声；slide_down 下滑音', 'dur', at='peak')
def _slide(e, ctx):
    if e['type'] == 'slide_down': return tone_glide(620, 140, max(0.4, e.get('dur', 0.6)), 0.45), 0.35, e.get('pan', 0.0), 0.3
    return sweep_noise(0.38, 900, 2600, 0.5, 'hump', 0.5), 0.3, e.get('pan', 0.0), 0.15
@fx_('swell blur_swell', '和弦音由弱渐强，跟随当前和弦；blur_swell 带噪声', 'dur', at='end')
def _swell_fx(e, ctx):
    dd = max(0.6, e.get('dur', 0.6) if e['type'] == 'swell' else 1.6); n = int(dd * SR); t = tt(n); y = np.zeros(n)
    root, notes = ctx['chord_at'](e['t'])
    for m in notes[1:4]:
        for dt in (-0.08, 0.08): y += np.sin(2 * math.pi * mtof(m + 12) * 2 ** (dt / 12) * t)
    y *= (t / dd) ** 2 * np.exp(-np.maximum(0, t - dd * 0.85) / 0.15)
    if e['type'] == 'blur_swell': y = P(y, sweep_noise(dd, 400, 1600, 0.6, 'swell'))
    return lp(y, 2500), 0.12, e.get('pan', 0.0), 0.6
@fx_('chord_lift', '钢琴琶音上扬，章节开头', '')
def _chord_lift(e, ctx):
    out = np.zeros(int(3.2 * SR))
    for j, m in enumerate([65, 69, 72, 76, 79, 84]): y = piano(m + 12, 2.2, 0.42, 1.3)[:len(out) - int(j * 0.025 * SR)]; i = int(j * 0.025 * SR); out[i:i + len(y)] += y
    return out, 0.4, e.get('pan', 0.0), 0.55
@fx_('title_rise', '三个高音渐强，标题升起', '', at='peak')
def _title_rise(e, ctx):
    n = int(SR); t = tt(n); y = np.zeros(n)
    for m in (86, 90, 93): y += np.sin(2 * math.pi * mtof(m) * t) * t * np.exp(-np.maximum(0, t - 0.6) / 0.12)
    return y, 0.05, e.get('pan', 0.0), 0.6
@fx_('rails car_move', '低频滑行：rails 轨道，car_move 卡片平移', 'dur', at='peak')
def _rails(e, ctx):
    if e['type'] == 'rails': return lp(sweep_noise(max(0.5, e.get('dur', 0.6)), 150, 600, 0.6, 'hump'), 900), 0.4, e.get('pan', 0.0), 0.2
    return lp(sweep_noise(max(0.3, e.get('dur', 0.6)), 120, 420, 0.6, 'hump'), 700), 0.5, e.get('pan', 0.0), 0.15
