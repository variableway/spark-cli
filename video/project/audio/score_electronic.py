"""电子乐 / 氛围乐配乐（style=electronic | ambient）：按 music.sections 的拍号分段编排，底鼓只放在 music.kicks 的拍上。

每种 section type 决定声部、滤波开合和力度（表在 TABLE / AMB_PATCH，参数含义见 BASE）：
  intro   铺底滤波慢慢打开 + 轻 8 分踩镲 + 次低频；结尾一声反向镲      钩子、开场
  groove  铺底 + 十六分琶音 + 反拍低音 + 踩镲 + 拍手；起点一声镲        展示、主体
  build   琶音越来越亮、踩镲渐强、军鼓滚奏加密（8 分→16 分→32 分）、上升音、铺底滤波打开、整体变薄（高通抬高）
  gap     全部静音（含混响尾巴）；音效不受影响                          drop 前的一口气，通常 1/4 到 1 拍
  drop    最满：重底鼓侧链、7 把锯齿和弦、十六分低音 + 次低频、主旋律、起点镲 + 次低频下坠
  break   铺底 + 稀疏琶音，无鼓点（底鼓照 kicks）                       情绪缓一下
  outro   和弦长音按指数衰减 + 一串上行玻璃音 + 起点低频轰鸣            落版
section 里可以直接写 BASE 里的任何键覆盖该段（如 {"from":4,"to":8,"type":"groove","arp":0,"level":1.2}）。
style=ambient：同一套结构，换成钟音琶音、无踩镲拍手军鼓、drop 无主旋律，适合产品/界面类的平静氛围。"""
import math
import numpy as np
from scipy.ndimage import uniform_filter1d
import instruments as I
import harmony as H
from instruments import SR, S, tt, mtof, Bus

# 键的含义：pad 铺底音量；cut 铺底低通起止 Hz（段内线性渐变）；voices/spread 超锯齿把数/失谐；decay 铺底衰减秒数(0=不衰减)；
# arp 每拍几个琶音音(0=无)；arp_g 琶音音量；arp_bright 起止亮度；inst pluck|bell；hat 0 无/1 轻 8 分/2 十六分/3 十六分渐强/4 十六分加开镲；
# clap 在 2、4 拍；roll 段尾军鼓滚奏；bass sub|hold|off8|pump；lead 主旋律；riser 整段上升音；rev_end 段尾反向镲拍数；
# hit (镲力度, 次低频下坠力度) 段首；sparkle 段首上行玻璃音；hp 高通起止 Hz（变薄）；level 整段音量倍数；sc 侧链深度 0..1（只在有底鼓时生效）
BASE = dict(pad=0, cut=(2500, 2500), voices=5, spread=0.3, decay=0, arp=0, arp_g=1.0, arp_bright=(0.4, 0.6), inst='pluck', hat=0, clap=0, roll=0,
            bass=None, lead=0, riser=0, rev_end=0, hit=None, sparkle=0, hp=None, level=1.0, sc=0.5)
TABLE = {
    'intro':  dict(pad=0.8, cut=(350, 2200), hat=1, bass='sub', rev_end=1.5, level=0.8, sc=0.3),
    'groove': dict(pad=0.7, cut=(2000, 2600), arp=4, arp_g=0.9, arp_bright=(0.35, 0.6), hat=2, clap=1, bass='off8', hit=(0.55, 0), level=0.95, sc=0.5),
    'build':  dict(pad=0.8, cut=(1500, 7000), arp=4, arp_bright=(0.4, 1.0), hat=3, clap=1, roll=1, bass='off8', riser=1, rev_end=2, hp=(60, 400), level=0.95, sc=0.55),
    'gap':    dict(),
    'drop':   dict(pad=1.0, voices=7, spread=0.34, cut=(4200, 4200), arp=4, arp_g=0.7, arp_bright=(0.8, 0.8), hat=4, clap=1, bass='pump', lead=1, hit=(0.8, 0.5), level=1.1, sc=0.8),
    'break':  dict(pad=0.8, cut=(900, 1800), arp=2, arp_g=0.7, arp_bright=(0.3, 0.5), bass='sub', rev_end=1.5, level=0.8, sc=0.3),
    'outro':  dict(pad=0.9, cut=(3000, 3000), decay=2.4, bass='hold', hit=(0.3, 0.8), sparkle=1, level=0.9, sc=0.3),
}
AMB_PATCH = {
    'intro': dict(arp=0.5, inst='bell', hat=0), 'groove': dict(pad=1.0, cut=(1500, 2200), arp=1, inst='bell', hat=0, clap=0, bass='sub', hit=None),
    'build': dict(arp=2, inst='bell', hat=0, clap=0, roll=0, bass='sub'), 'drop': dict(arp=2, inst='bell', hat=0, clap=0, bass='sub', lead=0, hit=(0.5, 0.6), cut=(3500, 3500)),
    'break': dict(arp=0.5, inst='bell'), 'outro': dict(),
}
PAT = [0, 2, 4, 2, 1, 3, 4, 3]
LEAD = [(0, .5, 2), (.75, .25, 1), (1, .5, 2), (1.75, .25, 3), (2, .75, 4), (2.75, .25, 3), (3, .5, 2), (3.5, .5, 1)]     # (拍内位置, 时值, 和弦音序号)


def norm_sections(E, table):
    raw = E.MU.get('sections'); nb = (E.TOTAL - E.OFFSET) / E.BEAT
    if not raw:
        q = max(4, round(nb / 4 / 4) * 4)      # 默认三段：约 1/4 intro，中间 groove，约 1/4 outro（按小节取整）
        raw = [{'from': 0, 'to': q, 'type': 'intro'}, {'from': q, 'to': max(q, nb - q), 'type': 'groove'}, {'from': max(q, nb - q), 'to': nb, 'type': 'outro'}]
        print(f'!! music.sections 没写，用默认三段：intro 0–{q}、groove {q}–{max(q, nb - q):g}、outro 到 {nb:g} 拍。要 build / gap / drop 请自己写 sections')
    out = []
    for r in sorted(raw, key=lambda r: r['from']):
        if r['type'] not in table: raise SystemExit(f"section type {r['type']!r} 不存在。可用：{' '.join(table)}")
        if out and r['from'] < out[-1]['b1'] - 1e-6: raise SystemExit(f"sections 重叠：{out[-1]['type']} 到 {out[-1]['b1']} 拍，{r['type']} 从 {r['from']} 拍开始")
        p = {**BASE, **table[r['type']], **{k: v for k, v in r.items() if k in BASE}}
        out.append({**p, 'type': r['type'], 'b0': r['from'], 'b1': r['to'], 't0': E.OFFSET + r['from'] * E.BEAT, 't1': E.OFFSET + r['to'] * E.BEAT})
    if out and out[-1]['t1'] < E.TOTAL - 0.5: print(f"!! 最后一段 {out[-1]['type']} 在 {out[-1]['t1']:.2f}s 结束，之后到片尾 {E.TOTAL:.2f}s 没有配乐")
    return out


def act_rms(x, floor_db=-45):
    """有声部分的 RMS（dB）：只统计包络高于该声部最大值 floor_db 以下的采样，避免静音段把电平拉低"""
    m = x.mean(0) if x.ndim == 2 else x; e = np.sqrt(np.maximum(uniform_filter1d(m ** 2, int(0.05 * SR)), 0) + 1e-18); k = e > e.max() * 10 ** (floor_db / 20)
    return 20 * np.log10(np.sqrt((m[k] ** 2).mean()) + 1e-12) if k.any() else -120.0


def harmony(E):
    """key / progression / chord_beats → (主音, 是否小调, chord_b(拍)→和弦, chord_segs(b0,b1), 音效用 ctx, 每和弦拍数)"""
    MU, BEAT, OFF = E.MU, E.BEAT, E.OFFSET
    tonic, minor = H.parse_key(MU.get('key', 'A minor'))
    CHS = [H.chord(n) for n in (MU.get('progression') or H.default_progression(tonic, minor))]; cb = float(MU.get('chord_beats', 4))
    def chord_b(beat): return CHS[int(math.floor(beat / cb + 1e-9)) % len(CHS)]
    def chord_segs(b0, b1):
        b = b0
        while b < b1 - 1e-9: nb = min(b1, (math.floor(b / cb + 1e-9) + 1) * cb); yield b, nb, chord_b(b); b = nb
    SCALE = H.scale_notes(tonic, minor)
    ctx = {'chord_at': lambda t: H.five(chord_b((t - OFF) / BEAT)), 'chords': [H.five(c) for c in CHS], 'scale': lambda n, base=0: SCALE[int(base + n) % len(SCALE)]}
    return tonic, minor, chord_b, chord_segs, ctx, cb


def render(E):
    N, TOTAL, BEAT, OFF, MU = E.N, E.TOTAL, E.BEAT, E.OFFSET, E.MU; amb = E.style == 'ambient'
    rng = np.random.default_rng(E.seed + 1); tb = lambda b: OFF + b * BEAT
    table = {t: {**v, **(AMB_PATCH.get(t, {}) if amb else {})} for t, v in TABLE.items()}
    tonic, minor, chord_b, chord_segs, ctx, cb = harmony(E)
    secs = norm_sections(E, table); sec_at = lambda beat: next((s for s in secs if s['b0'] - 1e-6 <= beat < s['b1'] - 1e-6), None)
    music, mrev, bass, perc, drev = (Bus(n, N) for n in 'music mrev bass perc drev'.split())
    def jit(ms=2): return rng.normal(0, ms / 1000)

    # ------------------------------------------------------------ 铺底（超锯齿和弦，滤波随 section 开合）
    pad = np.zeros((2, N + SR * 4))
    for s in secs:
        if not s['pad']: continue
        for b0, b1, ch in chord_segs(s['b0'], s['b1']):
            dur = (b1 - b0) * BEAT; i = S(tb(b0))
            if i >= N: continue
            for m in ch['notes'][:4] + [ch['bass'] + 12]:
                y = I.supersaw(m, dur, s['voices'], s['spread'], 0.12, 0.006 if s['type'] == 'drop' else 0.03) * 0.18 * s['pad']
                if s['decay']: y = y * np.exp(-tt(y.shape[1]) / s['decay'])
                n = min(y.shape[1], pad.shape[1] - i); pad[:, i:i + n] += y[:, :n]
    def curve(f, default, log=False):
        xs, ys = [], []
        for s in secs: v0, v1 = f(s); xs += [s['t0'], max(s['t0'] + 1e-4, s['t1'] - 1e-3)]; ys += [v0, v1]
        if not xs: return np.full(N, default)
        return np.exp(np.interp(tt(N), xs, np.log(ys))) if log else np.interp(tt(N), xs, ys)
    pad = I.filt_auto(pad[:, :N], curve(lambda s: s['cut'], 2500, True), 'low')
    music.L[:N] += pad[0]; music.R[:N] += pad[1]; mrev.L[:N] += pad[0] * 0.15; mrev.R[:N] += pad[1] * 0.15

    # ------------------------------------------------------------ 逐段编排
    for s in secs:
        b0, b1, ty = s['b0'], s['b1'], s['type']; L = b1 - b0
        if ty == 'gap' or L <= 0: continue
        if s['hit']:                                                                 # 段首：镲 + 次低频下坠 / 轰鸣
            c, sb = s['hit']
            if c: y = I.d_crash(c); perc.add(tb(b0), y, 0.35, 0.25); mrev.add(tb(b0), y, 0.2)
            if sb: perc.add(tb(b0), I.sub_drop(1.4, 90, 32), 0.5 * sb, 0)
        if s['riser']: perc.add(tb(b0), I.riser_noise(max(0.3, L * BEAT - 0.05)), 0.3, 0)
        if s['rev_end']:
            d = min(s['rev_end'], L) * BEAT; perc.add(tb(b1) - d, I.rev_cymbal(d), 0.4, 0.2)
        if s['sparkle']:
            for j in range(8):
                y = I.glass(H.scale_notes(tonic, minor)[10 + j] + 12, 0.5, 0.3); t = tb(b0) + 0.3 * BEAT + j * BEAT / 4; music.add(t, y, 0.12, -0.5 + 0.14 * j); mrev.add(t, y, 0.14)
        if s['roll']:                                                                 # 军鼓滚奏：8 分 → 16 分 → 32 分，渐强升调
            R = min(8.0, L); r0 = b1 - R; b = r0
            while b < b1 - 1e-6:
                u = (b - r0) / R; y = I.d_snare(1, 0.09, 7 * u); perc.add(tb(b), y, 0.14 + 0.3 * u, 0.08); drev.add(tb(b), y, 0.1)
                b += 1 / (2 if u < 0.34 else 4 if u < 0.67 else 8)
        # 踩镲 / 拍手（绝对拍格：第 1、3 拍 = 小节的 1、2 拍…；拍手落在 2、4 拍）
        if s['hat']:
            for j in range(math.ceil(b0 * 4 - 1e-9), math.ceil(b1 * 4 - 1e-9)):
                pos = j % 4; u = (j / 4 - b0) / L
                w = [0.10, 0, 0.16, 0][pos] if s['hat'] == 1 else [0.16, 0.10, 0.34, 0.12][pos] * (0.5 + u if s['hat'] == 3 else 1.1 if s['hat'] == 4 else 1)
                if w: perc.add(tb(j / 4) + jit(), I.d_hat(w, s['hat'] == 4 and pos == 2), 1.0, 0.3 if pos % 2 else -0.2)
        if s['clap']:
            for k in range(math.ceil(b0 - 1e-9), math.ceil(b1 - 1e-9)):
                if k % 2 == 1: y = I.d_clap(0.8); perc.add(tb(k), y, 0.5, 0.05); drev.add(tb(k), y, 0.12)
        # 琶音
        if s['arp']:
            step = 1 / s['arp']; i = 0
            while b0 + i * step < b1 - 1e-9:
                beat = b0 + i * step; tones = [m + 12 for m in chord_b(beat)['notes']]; m = tones[PAT[i % 8] % len(tones)]; u = (beat - b0) / L
                br = s['arp_bright'][0] + (s['arp_bright'][1] - s['arp_bright'][0]) * u; acc = i % 4 == 0
                y = I.lp(I.synth_pluck(m, min(0.3, step * BEAT * 0.9), br + (0.2 if acc else 0), 1.0), 4200) if s['inst'] == 'pluck' else I.bell(mtof(m + 12), 1.6, 0.5) * 2
                g = 0.22 * s['arp_g'] * (1 if acc else 0.75); music.add(tb(beat), y, g, 0.4 * (1 if i % 2 else -1)); mrev.add(tb(beat), y, g * 0.8)
                i += 1
        # 低音
        if s['bass'] in ('sub', 'hold'):
            for sb0, sb1, ch in chord_segs(b0, b1):
                d = (sb1 - sb0) * BEAT; n = int((d + 0.1) * SR); x = tt(n)
                sb = ch['bass'] - (12 if ch['bass'] >= 42 else 0)      # 次低频：折到 30–41（46–87 Hz）
                y = (np.sin(2 * np.pi * mtof(sb) * x) + 0.15 * np.sin(4 * np.pi * mtof(sb) * x)) * np.minimum(1, x / (min(1.5, d * 0.6) if ty == 'intro' else 0.05)) * np.exp(-np.maximum(0, x - d) / 0.05)
                if s['bass'] == 'hold': y *= np.exp(-x / 1.5)
                bass.add(tb(sb0), y, 0.4, 0)
        elif s['bass'] == 'off8':
            for k in range(math.ceil(b0 - 1e-9), math.ceil(b1 - 1e-9)):
                if k + 0.5 < b1: bass.add(tb(k + 0.5), I.e_bass(chord_b(k)['bass'] + (12 if k % 4 == 3 else 0) + 12, BEAT * 0.4), 0.42, 0)
        elif s['bass'] == 'pump':
            for k in range(math.ceil(b0 - 1e-9), math.ceil(b1 - 1e-9)):
                r = chord_b(k)['bass'] + 12
                for q, v in ((0.25, 0.8), (0.5, 1.0), (0.75, 0.8)):
                    if k + q < b1: bass.add(tb(k + q), I.e_bass(r, BEAT * 0.22), 0.42 * v, 0)
                n = int(BEAT * SR); x = tt(n); bass.add(tb(k) + 0.02, np.sin(2 * np.pi * mtof(r - 12 - (12 if r - 12 >= 42 else 0)) * x) * np.minimum(1, x / 0.01) * np.exp(-x / 0.6), 0.34, 0)
        # 主旋律
        if s['lead']:
            for j, bar in enumerate(np.arange(b0, b1 - 1e-9, 4.0)):
                notes = chord_b(bar)['notes']; T = [m + 12 for m in notes] + [m + 24 for m in notes]
                for pos, dur, idx in LEAD:
                    if bar + pos >= b1 - 1e-9: continue
                    y = I.lead_note(T[min(len(T) - 1, idx + (1 if j % 2 else 0))], dur * BEAT); music.add(tb(bar + pos), y, 0.12, 0.12); mrev.add(tb(bar + pos), y, 0.22)

    # ------------------------------------------------------------ 底鼓：只放在 music.kicks 的拍上，与画面缩放一致
    sc = np.ones(N + SR * 4); kicks = []
    for k in E.kicks:
        s = sec_at(k)
        if s and s['type'] == 'gap': print(f'!! 拍 {k:g} 的底鼓落在 gap 段里，已跳过（画面仍会在这一拍缩放，建议把 kicks 区间避开 gap）'); continue
        if tb(k) >= TOTAL: continue
        ty = s['type'] if s else 'groove'; heavy = ty == 'drop'
        perc.add(tb(k), I.d_kick(1.0 if heavy else 0.95, heavy, 0.34 if heavy else 0.5 if ty == 'outro' else 0.28), 0.95, 0); kicks.append(tb(k))
        i = S(tb(k)); n = int(0.32 * SR); x = tt(n); env = 1 - (s['sc'] if s else 0.5) * np.exp(-x / 0.09) * np.minimum(1, x / 0.004) ** 0.5
        sc[i:i + n] = np.minimum(sc[i:i + n], env[:len(sc[i:i + n])])
    sc = uniform_filter1d(sc, 64)[:N]

    # ------------------------------------------------------------ 成轨：侧链、变薄、段落电平、gap 静音、各声部定电平
    RV = I.reverb(mrev, 2.4, 4, 6000); DR = perc.st() + 0.5 * I.reverb(drev, 0.9, 3, 7000)
    M = music.st() * sc + RV * (0.6 + 0.4 * sc); B = bass.st() * sc
    hpc = curve(lambda s: s['hp'] or (20, 20), 20, True)
    if hpc.max() > 25: M = I.filt_auto(M, hpc, 'high'); B = I.filt_auto(B, hpc, 'high')
    lev = uniform_filter1d(curve(lambda s: (s['level'], s['level']), 1.0), S(0.03))
    cover = np.zeros(N)
    for s in secs:
        if s['type'] != 'gap': cover[max(0, S(s['t0'])):min(N, S(s['t1']))] = 1
    cover = uniform_filter1d(cover, S(0.008))
    stems = {}
    for name, x, db in (('drums', DR, -23.0), ('music', M, -26.0), ('bass', B, -24.0)):
        x = x * lev * cover
        if act_rms(x) > -100: x = x * 10 ** ((db - act_rms(x)) / 20)
        stems[name] = x
    if not kicks: print('!! music.kicks 没写，所以没有底鼓和侧链。画面的底鼓缩放和音频底鼓都由 music.kicks 决定：要底鼓就在 project.json 写 "kicks": [[起拍, 止拍]]，两边会一起生效')
    return {'stems': stems, 'ctx': ctx, 'sections': [(s['t0'], s['t1'], s['type']) for s in secs], 'kicks': kicks}
