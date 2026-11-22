"""配音驱动的时间轴（timeline.mode = "voice"，通常经 tools/timeline.py 调用）：python3 tools/build_timeline.py [--estimate]
  默认：读 audio/narration.wav（由 tools/tts.py full 生成，任何配音后端都一样），按镜头之间 >=1 秒的静音切分镜头，
        再找出每个短句真实的开始时刻，解出拍点时间轴，拼出对齐后的人声轨。
  --estimate：还没有配音时，按音节估时（SPS）出一份临时时间轴，让画面可以先做；真实配音到位后重跑默认模式。
短句的开始时刻怎么来：
  1. 有 audio/narration.wav 对应的词级时间（audio/narration.words.json，edge-tts 合成时会写）就直接用词的开始时刻；
  2. 否则从音频里找：镜头内的每处短停顿（静音 >=0.04 秒）都是候选分界，用动态规划在候选里选出分界，
     使每个短句的发音时长和它的音节数成比例，跳过的长停顿罚分（长停顿几乎总在标点处）。分界取停顿结束、人声起音的时刻。
镜头分界：静音 >=1 秒的段数正好等于镜头数减一时直接用；对不上时（例如用户自己的录音）按同样的办法从 >=0.25 秒的静音里选，
  并列出选中的分界请你核对。
输出：timeline.json、web/timeline.js、web/project.js、audio/voice_aligned.wav（仅默认模式）、index.html 的脚本列表
镜头切在拍上，章节切在两拍的整数倍上，镜头的画面动作用 ph(id,k)（第 k 个短句的开始时刻）对齐配音。
每个镜头的运动标签和 beats 模式一样写在 timeline.shots：[{"id": "S04", "motion": "可以震"}]，没写的镜头是「稳」。
短句（timeline.json 每个镜头的 phrases）：{text 中文短句, en 英文译文（vo.json 写了才有）, t0, t1 对齐后的起止秒, src_t0, src_t1}。
  字幕层（project.json 的 subtitles）和 tools/srt.py 都读这份数据，二者一致。
  译文写在 vo.json 每个镜头的 "en": ["...", ...]，按短句顺序一句一条。subtitles.langs 里配音语言以外的语言（中文配音的 en），
  短句缺译文或条数不对时列出来并停下。配音语言按短句有没有汉字定（有算 zh，否则算 en），和字幕层一致。
project.json 用到的键：chapters、timing、voice、timeline.bpm（缺省 80）、timeline.shots（可选：motion、label）、subtitles.langs。"""
import difflib, json, math, re, sys
import numpy as np
import scipy.io.wavfile as wavfile
from common import ROOT, project, vo, vo_tr, voice_lang, subtitles
from syl import syl, pauses, phrases, SPS
from tl_io import write_all

EST = '--estimate' in sys.argv
cfg = project()
VO, _ = vo()
ids = [i for i, _ in VO]
VOD = dict(VO)
TR = vo_tr()


def check_langs():
    """字幕要的语言里，配音语言以外的（例如中文配音的 en），每个短句都要有译文：vo.json 的 "en" 是列表，第 k 条对应第 k 个短句。
    缺的、条数不对的都列出来并停下。没开字幕时，写了的译文也要条数对得上。"""
    langs = subtitles(cfg)['langs']; bad = []
    for sid, text in VO:
        ph = phrases(text); vl = voice_lang(text)
        for lang in sorted(set([l for l in langs if l != vl]) | set(TR.get(sid) or {})):
            v = (TR.get(sid) or {}).get(lang)
            if v is None: bad.append((sid, lang, ph, None, f'没有 {lang}')); continue
            if not isinstance(v, list) or len(v) != len(ph) or not all(isinstance(x, str) and x.strip() for x in v):
                bad.append((sid, lang, ph, v if isinstance(v, list) else None,
                            f'{lang} 要写成列表，每个短句一条：这个镜头切出 {len(ph)} 个短句，{lang} 是 {len(v) if isinstance(v, list) else type(v).__name__}（空的条目也算缺）'))
    if bad:
        print(f'字幕语言 {"+".join(langs)}（project.json 的 subtitles.langs）。script/vo.json 里这些镜头的译文要补齐，按下面的短句顺序一句一条：')
        for sid, lang, ph, v, why in bad:
            print(f'  {sid}：{why}')
            for k, p in enumerate(ph): print(f'    {k}. {p}' + (f'  →  {v[k]}' if v and k < len(v) else ''))
        sys.exit('补好后重跑 timeline.py。')


check_langs()
FPS = cfg.get('fps', 60)
BPM = (cfg.get('timeline') or {}).get('bpm', cfg.get('bpm', 80)); BEAT = 60 / BPM; BAR = 4 * BEAT
tm = cfg.get('timing', {})
LEAD = tm.get('lead', {}); HOLD = tm.get('hold', {})
DEF_LEAD = tm.get('defLead', 0.3); DEF_HOLD = tm.get('defHold', 0.25); TAIL = tm.get('tail', 0.45)
GAP = cfg.get('voice', {}).get('gap', 1.4)
SHOTS = {s['id']: s for s in (cfg.get('timeline') or {}).get('shots', [])}


def expand(spec):
    if isinstance(spec, list):
        return spec
    a, b = spec.split('-')
    pre = re.match(r'[A-Za-z]+', a).group(0)
    return ['%s%02d' % (pre, i) for i in range(int(a[len(pre):]), int(b[len(pre):]) + 1)]


CHAPTERS = [(c['id'], expand(c['scenes'])) for c in cfg['chapters']]
used = [s for _, l in CHAPTERS for s in l]
assert used == ids, f'chapters 里的镜头顺序必须和 vo.json 完全一致：\n  chapters={used}\n  vo={ids}'
if set(SHOTS) - set(ids):
    raise SystemExit(f'timeline.shots 里这些镜头不在 vo.json 里：{sorted(set(SHOTS) - set(ids))}')

# ---------------------------------------------------------------- 1. 每个镜头的人声时长与短句时刻（相对配音音频）
HOP = 0.005


def runs(mask, minlen, base=0.0):
    """mask 里连续为真、长度 >=minlen 秒的区间 [(开始, 结束)]（秒，加上 base）"""
    out = []; s = None; n = len(mask)
    for i, v in enumerate(mask):
        if v and s is None: s = i
        if (not v) and s is not None:
            if (i - s) * HOP >= minlen: out.append((base + s * HOP, base + i * HOP))
            s = None
    if s is not None and (n - s) * HOP >= minlen: out.append((base + s * HOP, base + n * HOP))
    return out


def segment(on, off, P, counts, full=0.35):
    """在 [on, off] 内的停顿 P = [(开始, 结束)] 里选 len(counts)-1 处做分界，返回所选停顿的序号。
    代价：每段的发音时长（去掉段内停顿）和「音节数 × 平均每音节时长」之比取对数的平方；
    段内跳过的停顿按长度罚分（>=full 秒罚满 1.5）。停顿不够时返回 None。"""
    K, M = len(counts), len(P)
    if K == 1: return []
    if M < K - 1: return None
    pl = [b - a for a, b in P]
    cum = np.concatenate([[0], np.cumsum(pl)])
    cpen = np.concatenate([[0], np.cumsum([1.5 * min(1.0, d / full) for d in pl])])
    R = max(0.02, (off - on) - cum[-1]) / sum(counts)

    def cost(k, a, b):          # 第 k 段从停顿 a 之后到停顿 b 之前（a = -1 是 on，b = M 是 off）
        t0 = on if a < 0 else P[a][1]; t1 = off if b >= M else P[b][0]
        inner = cum[b] - cum[a + 1] if b > a + 1 else 0.0
        skip = cpen[b] - cpen[a + 1] if b > a + 1 else 0.0
        v = max(0.02, t1 - t0 - inner)
        return math.log((v + 0.15) / (R * counts[k] + 0.15)) ** 2 + skip
    INF = float('inf')
    dp = [[INF] * (M + 1) for _ in range(K)]; bk = [[-1] * (M + 1) for _ in range(K)]
    for b in range(M): dp[0][b] = cost(0, -1, b)
    for k in range(1, K):
        for b in ([M] if k == K - 1 else range(k, M)):
            for a in range(k - 1, b):
                if dp[k - 1][a] < INF:
                    c = dp[k - 1][a] + cost(k, a, b)
                    if c < dp[k][b]: dp[k][b], bk[k][b] = c, a
    if dp[K - 1][M] == INF: return None
    out = []; b = M
    for k in range(K - 1, 0, -1):
        b = bk[k][b]; out.append(b)
    return out[::-1]


def norm(s):
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]', '', s.lower())


def word_starts(dur):
    """词级时间 → {镜头: [各短句开始时刻]}；没有词级时间或和配音对不上时返回 {}"""
    f = ROOT / 'audio' / 'narration.words.json'
    if not f.exists(): return {}
    d = json.load(open(f, encoding='utf-8'))
    if abs(d.get('duration', -1) - dur) > 0.05:
        print('  audio/narration.words.json 和 narration.wav 时长对不上（配音换过），不用词级时间'); return {}
    W = d['words']; wn = ''; owner = []
    for i, w_ in enumerate(W):
        n = norm(w_['text']); wn += n; owner += [(i, j, len(n)) for j in range(len(n))]
    tn = ''; first = []
    for sid, text in VO:
        for k, p in enumerate(phrases(text)):
            first.append((sid, k, len(tn))); tn += norm(p)
    m = [None] * len(tn)
    for a, b, size in difflib.SequenceMatcher(None, tn, wn, autojunk=False).get_matching_blocks():
        for j in range(size): m[a + j] = owner[b + j]
    out = {}
    for sid, k, pos in first:
        hit = next((m[j] for j in range(pos, min(pos + 3, len(m))) if m[j] is not None), None)
        if hit is None: out[sid] = None; continue
        i, j, n = hit; w_ = W[i]
        if out.get(sid, []) is not None:
            out.setdefault(sid, []).append(w_['t0'] + (w_['t1'] - w_['t0']) * j / n)
    return {k: v for k, v in out.items() if v}


scenes = []
SRC = '估算'
if EST:
    for sid in ids:
        t = VOD[sid]
        sp = syl(t) * SPS * (1.12 / cfg.get('voice', {}).get('speed', 1.12)) + pauses(t)
        ph = phrases(t); tot = sum(syl(p) for p in ph) or 1; acc = 0; out = []
        for p in ph:
            a = sp * acc / tot; acc += syl(p); out.append({'text': p, 'src_t0': a, 'src_t1': sp * acc / tot})
        for lang, v in (TR.get(sid) or {}).items():
            for o, e in zip(out, v): o[lang] = e.strip()
        scenes.append({'id': sid, 'src_on': 0.0, 'src_off': sp, 'speech': sp, 'phrases': out})
else:
    SR, x = wavfile.read(str(ROOT / 'audio' / 'narration.wav'))
    x = x.astype(np.float32) / (32768 if x.dtype == np.int16 else 1)
    if x.ndim > 1: x = x.mean(1)
    hop = int(HOP * SR); nfr = len(x) // hop
    rms = np.sqrt((x[:nfr * hop].reshape(nfr, hop) ** 2).mean(1)); db = 20 * np.log10(rms + 1e-9)
    DUR = len(x) / SR

    def fine(a, b, thr=-52):
        i0, i1 = int(a / HOP), int(b / HOP)
        idx = np.where(db[i0:i1] > thr)[0]
        return (i0 + idx[0]) * HOP, (i0 + idx[-1] + 1) * HOP

    gaps = runs(db < -45, 1.0)
    voice_on, voice_off = fine(0, DUR)
    gaps = [g for g in gaps if voice_on < g[0] and g[1] < voice_off]
    if len(gaps) != len(VO) - 1:
        cand = [g for g in runs(db < -45, 0.25) if voice_on < g[0] and g[1] < voice_off]
        pick = segment(voice_on, voice_off, cand, [syl(t) for _, t in VO], full=1.0)
        if pick is None:
            raise SystemExit(f'配音里只找到 {len(cand)} 处 >=0.25 秒的静音，不够切出 {len(VO)} 个镜头。'
                             f'合成的配音：镜头之间用 <#{GAP}#>，镜头内部的停顿标记必须 <1.0 秒；录音：镜头之间停顿 1 秒以上。')
        gaps = [cand[i] for i in pick]
        print(f'  配音里 >=1 秒的静音有 {len(runs(db < -45, 1.0))} 处，应为 {len(VO) - 1} 处；已按音节比例选出镜头分界，请核对：')
        for (sid, t), g in zip(VO[1:], gaps):
            head = re.sub(r'<#[\d.]+#>|\(\w+\)', '', t)[:16]
            print(f'    {sid} 从 {g[1]:7.2f}s 开始（前面停顿 {g[1] - g[0]:.2f}s）：{head}…')
    bounds = [0.0] + [(a + b) / 2 for a, b in gaps] + [DUR]
    WS = word_starts(DUR)
    SRC = '词级时间' if WS else '停顿与起音点'

    for i, (sid, text) in enumerate(VO):
        on, off = fine(bounds[i], bounds[i + 1]); ph = phrases(text)
        counts = [syl(p) for p in ph]
        inner = [g for g in runs(db[int(on / HOP):int(off / HOP)] < -40, 0.04, on) if on + 0.05 < g[0] and g[1] < off - 0.05]
        ws = WS.get(sid)
        if ws and len(ws) == len(ph) and all(on - 0.3 <= a < off for a in ws) and all(b > a for a, b in zip(ws, ws[1:])):
            starts = [on] + ws[1:]
        else:
            pick = segment(on, off, inner, counts)
            if pick is not None:
                starts = [on] + [inner[j][1] for j in pick]
            else:                                    # 停顿比短句少：按发音时长比例估
                voiced = (off - on) - sum(b - a for a, b in inner); tot = sum(counts); starts = []; cum = 0

                def vt2abs(v):
                    t = on; rem = v
                    for a, b in inner:
                        if a - t >= rem: return t + rem
                        rem -= (a - t); t = b
                    return t + rem
                for c in counts:
                    starts.append(vt2abs(voiced * cum / tot)); cum += c
        starts = [round(a, 3) for a in starts]
        ends = []
        for k in range(len(ph)):
            nxt = starts[k + 1] if k < len(ph) - 1 else off
            cc = [a for a, b in inner if starts[k] + 0.15 < a <= nxt + 0.01]
            ends.append(round(max(cc) if (cc and k < len(ph) - 1) else nxt, 3))
        scenes.append({'id': sid, 'src_on': round(on, 3), 'src_off': round(off, 3), 'speech': round(off - on, 3),
                       'phrases': [dict({'text': p, 'src_t0': a, 'src_t1': e}, **{lang: v[k].strip() for lang, v in (TR.get(sid) or {}).items()})
                                   for k, (p, a, e) in enumerate(zip(ph, starts, ends))]})

# ---------------------------------------------------------------- 2. 解时间轴：镜头切在拍上，章节切在两拍的整数倍上
SC = {s['id']: s for s in scenes}
t = 0.0
for cid, lst in CHAPTERS:
    c0 = t
    for sid in lst:
        s = SC[sid]; s['chapter'] = cid
        need = LEAD.get(sid, DEF_LEAD) + s['speech'] + TAIL + HOLD.get(sid, DEF_HOLD)
        s['beats'] = math.ceil(need / BEAT - 1e-6)
        s['t0'] = round(t, 4); s['dur'] = round(s['beats'] * BEAT, 4); s['t1'] = round(t + s['dur'], 4); t += s['dur']
    pad = math.ceil((t - c0) / (2 * BEAT) - 1e-6) * (2 * BEAT) - (t - c0)
    s = SC[lst[-1]]; s['beats'] += round(pad / BEAT); s['dur'] = round(s['dur'] + pad, 4); s['t1'] = round(s['t1'] + pad, 4); t += pad
for cid, lst in CHAPTERS:
    for sid in lst:
        s = SC[sid]; lead = LEAD.get(sid, DEF_LEAD)
        s['v0'] = round(s['t0'] + lead, 3); shift = s['v0'] - s['src_on']
        s['v1'] = round(s['src_off'] + shift, 3)
        for p in s['phrases']:
            p['t0'] = round(p['src_t0'] + shift, 3); p['t1'] = round(p['src_t1'] + shift, 3)
        s['shift'] = round(shift, 4)
TOTAL = round(t, 4)

# ---------------------------------------------------------------- 3. 拼人声轨
if not EST:
    SRo = SR
    out = np.zeros(int(TOTAL * SRo) + SRo, np.float32); FADE = int(0.012 * SRo)
    for s in scenes:
        a = max(0, int((s['src_on'] - 0.06) * SRo)); b = min(len(x), int((s['src_off'] + 0.12) * SRo))
        seg = x[a:b].copy(); seg[:FADE] *= np.linspace(0, 1, FADE); seg[-FADE:] *= np.linspace(1, 0, FADE)
        d = int((s['src_on'] - 0.06 + s['shift']) * SRo); out[d:d + len(seg)] += seg
    out = out[:int(TOTAL * SRo)]
    wavfile.write(str(ROOT / 'audio' / 'voice_aligned.wav'), SRo, (out * 32767).astype(np.int16))

tl = {'mode': 'voice', 'fps': FPS, 'total': TOTAL, 'bpm': BPM, 'beat': BEAT, 'bar': BAR, 'offset': 0.0, 'estimate': EST,
      'chapters': [{'id': c, 'scenes': l, 't0': SC[l[0]]['t0'], 't1': SC[l[-1]]['t1']} for c, l in CHAPTERS],
      'scenes': {s['id']: dict({k: s[k] for k in ['id', 'chapter', 't0', 't1', 'dur', 'beats', 'v0', 'v1', 'shift', 'phrases']},
                               label=SHOTS.get(s['id'], {}).get('label', ''),
                               motion='可以震' if SHOTS.get(s['id'], {}).get('motion') == '可以震' else '稳') for s in scenes}}
msg = write_all(tl, cfg)

print(('估算' if EST else '真实配音') + f'时间轴：{TOTAL:.1f} 秒（{int(TOTAL // 60)} 分 {TOTAL % 60:.0f} 秒），{len(scenes)} 个镜头，{BPM} BPM；短句时刻来自{SRC}')
print(msg)
for c in tl['chapters']:
    print(f"  {c['id']:10s} {c['t0']:7.2f}–{c['t1']:7.2f}  ({c['t1'] - c['t0']:5.1f}s)")
for s in scenes:
    print(f"  {s['id']} {s['t0']:7.3f}–{s['t1']:7.3f} ({s['beats']:2d}拍)  人声 {s['v0']:7.2f}–{s['v1']:7.2f}  尾 {s['t1'] - s['v1']:4.2f}s  {tl['scenes'][s['id']]['motion']}")
