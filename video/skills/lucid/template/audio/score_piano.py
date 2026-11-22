"""钢琴织体配乐（style=piano，讲解片默认）：v1 的做法，按 chapter 选织体。music 字段：
  key：'F' / 'D' / 'C' / 'G' / 'A' / 'E' / 'B♭'（大调；和弦进行 I–vi–IV–V，每个和弦 2 小节；不读 progression）
  roles：每个 chapter id 对应一种织体
     sparse   只有铺底和稀疏的钢琴单音（引入、信息密集的分析段）
     groove   钢琴八分音符律动 + 低音 + 底鼓（主体叙述）
     arp      在 groove 之上加琴弦琶音（推进、收束）
     minor    转小调：持续低音 + 细密滴答（风险、反证；与 minor_span 一起用）
     outro    收尾长音
  heartbeat：[[起始 id@短句序号 或 秒, 结束 …], …] 心跳段（两拍一次，与画面里的波纹同步）；心跳段内不放底鼓
  quiet：[[秒, 秒], …] 近乎静音的段落（一句关键原话前后留白）
  insights：[镜头 id, …] 用长音钢琴代替律动的「启示页」
  minor_span：[起, 终] 小调持续的时间范围（秒或 id@短句序号）
  groove_start / tail_chord_at / final_chord_before_end：律动开始、收束和终和弦的时刻（短片自动按比例收缩）
这里的底鼓是织体的一部分（讲解片没有画面底鼓同步），不读 music.kicks。"""
import math
import numpy as np
import instruments as I
import harmony as H
from instruments import SR, S, tt, lp, hp, noise, expdec, P, Bus, piano, pluck, kick, thud, nburst, mtof, reverb


def render(E):
    N, TOTAL, BEAT, BAR, MU, TL, RNG = E.N, E.TOTAL, E.BEAT, E.BAR, E.MU, E.TL, E.rng
    SC = TL['scenes']; CH = {c['id']: (c['t0'], c['t1']) for c in TL['chapters']}
    def PH(sid, k): p = SC[sid]['phrases']; return p[min(k, len(p) - 1)]['t0']
    def when(x):
        if isinstance(x, (int, float)): return float(x)
        if '@' in x: sid, k = x.split('@'); return PH(sid, int(k))
        return SC[x]['t0']

    # ------------------------------------------------------------ 调性与和声
    K0, _ = H.parse_key(MU.get('key', 'F'))
    def triad9(root_pc, minor):
        """(低音根音, [五个和弦音])：根、三度、五度、七度（大七/小七）、九度"""
        r = 36 + ((root_pc + K0) % 12); third = 3 if minor else 4; seventh = 10 if minor else 11
        return (r, [r + 12, r + 12 + third, r + 12 + 7, r + 12 + seventh, r + 12 + 14])
    MAJ = [triad9(0, False), triad9(9, True), triad9(5, False), triad9(7, False)]       # Imaj9, vim9, IVmaj9, V(add9)
    MIN = [triad9(9, True), triad9(5, False), triad9(2, True), triad9(4, False)]        # vi, IV, ii, iii：同一调里偏暗的循环
    PENT = [0, 2, 4, 7, 9]; SCALE = [60 + K0 + p + 12 * o for o in range(-1, 3) for p in PENT]
    def scale(n, base=0): i = int(base + n); return SCALE[min(len(SCALE) - 1, i % len(SCALE))]
    MS = MU.get('minor_span'); TR0, TR1 = (when(MS[0]), when(MS[1])) if MS else (1e9, 1e9)
    def chord_at(t):
        if TR0 <= t < TR1: return MIN[int((t - TR0) // (2 * BAR)) % 4]
        return MAJ[int(t // (2 * BAR)) % 4]
    ctx = {'chord_at': chord_at, 'chords': MAJ, 'scale': scale}

    roles = MU.get('roles', {}); ROLE = lambda t: next((roles.get(c, 'groove') for c, (a, b) in CH.items() if a <= t < b), 'outro')
    INS = set(MU.get('insights', []))
    def in_scene(t, *ids): return any(SC[i]['t0'] <= t < SC[i]['t1'] for i in ids)
    QUIET = [(when(a), when(b)) for a, b in MU.get('quiet', [])]
    HB = [(when(a), when(b)) for a, b in MU.get('heartbeat', [])]
    music = Bus('music', N); mrev = Bus('mrev', N)
    def automation(points, t): return np.interp(t, [p[0] for p in points], [p[1] for p in points])
    first = when(MU.get('groove_start', min(6.0, 0.25 * TOTAL)))             # 可写秒数或 '镜头@短句序号'

    # ------------------------------------------------------------ 铺底
    tline = tt(N); pad = np.zeros(N)
    for ci in range(int(TOTAL // (2 * BAR)) + 2):
        t0 = ci * 2 * BAR - 1.2; t1 = (ci + 1) * 2 * BAR + 1.2
        root, notes = chord_at(ci * 2 * BAR + 0.01)
        i0, i1 = max(0, S(t0)), min(N, S(t1)); n = i1 - i0
        if n <= 0: continue
        t = tt(n); y = np.zeros(n)
        for j, m in enumerate([notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[3] + 12, notes[4] + 12, root + 24]):
            f = mtof(m)
            for d in (-0.11, 0.0, 0.13):
                ph = RNG.uniform(0, 6.28); ff = f * 2 ** (d / 12 * 0.25)
                y += (np.sin(2 * math.pi * ff * t + ph) + 0.22 * np.sin(4 * math.pi * ff * t + ph * 1.3) + 0.08 * np.sin(6 * math.pi * ff * t)) * (0.9 if j < 5 else 0.5)
        e = np.ones(n); na = min(int(1.4 * SR), n // 2); e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2; e[-na:] = np.cos(np.linspace(0, np.pi / 2, na)) ** 2
        pad[i0:i1] += y * e
    pad = lp(pad, 1500, 2) * (1 + 0.12 * np.sin(2 * math.pi * 0.11 * tline))
    pts = [(0, 0), (min(3, first / 2), 0.55)]
    pts += [(max(pts[-1][0] + 0.1, when(first) - 1), 0.6), (when(first), 0.9)]
    for c, (a, b) in CH.items(): pts.append((a + 0.01, 0.8 if roles.get(c) == 'sparse' else 0.95))
    for a, b in QUIET: pts += [(a, 0.35), (b, 0.35), (b + 1.5, 0.9)]
    pts += [(TOTAL - 8, 0.9), (TOTAL - 0.5, 0.0), (TOTAL, 0)]
    pts = sorted(pts, key=lambda p: p[0])
    pad *= automation(pts, tline) * 0.022
    music.add(0, pad, 1.0, -0.15); music.add(0.011, pad, 1.0, 0.15); mrev.add(0, pad, 0.6, 0)

    # ------------------------------------------------------------ 编配
    HUM = np.random.default_rng(4242)
    def hum(t, ms=7): return t + HUM.normal(0, ms / 1000)
    def hv(v, k=0.13): return max(0.05, v * (1 + HUM.normal(0, k)))
    SWING = 0.016
    def phrase(t):
        u = (t % (2 * BAR)) / (2 * BAR); acc = 1.12 if abs((t % BAR)) < 0.02 else 1.0
        return (0.82 + 0.3 * math.sin(math.pi * min(1, u * 1.25))) * acc
    def beats(a, b):
        k = math.ceil(a / BEAT - 1e-9)
        while k * BEAT < b - 1e-9: yield k, k * BEAT; k += 1

    for t, m in [(0.8, 81), (3.05, 77), (4.55, 76), (6.05, 72)]:        # 开场：远处的钢琴单音动机
        if t > TOTAL * 0.7: continue
        m = m + (K0 - 5); y = piano(m, 1.6, 0.36, 0.8); music.add(t, y, 0.34, 0.3); mrev.add(t, y, 1.0, 0.3)

    hbs = lp(P(thud(58, 0.09, 0.9, 0.05), np.concatenate([np.zeros(int(0.2 * SR)), thud(50, 0.11, 0.7, 0.05)])), 400)   # 心跳：两拍一次
    for a, b in HB:
        k = math.ceil(a / (2 * BEAT))
        while k * 2 * BEAT < b:
            t = k * 2 * BEAT; g = 0.5 if t < b - 3 else 0.5 * max(0.2, (b - t) / 3); music.add(t, hbs, g, 0); k += 1

    PAT8 = [0, 2, 4, 2, 1, 3, 4, 3]; VEL8 = [0.55, 0.32, 0.45, 0.3, 0.5, 0.32, 0.44, 0.3]
    START = when(first); END_FULL = TOTAL - min(MU.get('tail_chord_at', 14.0), 0.7 * TOTAL)
    for k, t in beats(START, END_FULL):
        role = ROLE(t); root, notes = chord_at(t); b = k % 4; bar_k = int(t // BAR); upper = [m + 12 for m in notes]
        if any(a <= t < b2 for a, b2 in QUIET): continue
        ins = any(in_scene(t, i) for i in INS); hb = any(a <= t < b2 for a, b2 in HB)
        if role in ('groove', 'arp') and not ins:
            for h in (0, 1):
                idx = (b * 2 + h) % 8; tn = hum(t + h * (BEAT / 2 + SWING))
                y = piano(upper[PAT8[idx]], 1.1 + 0.2 * h, round(hv(VEL8[idx] * phrase(tn)), 2)); pan = -0.25 + 0.5 * (PAT8[idx] / 4)
                music.add(tn, y, 0.39, pan); mrev.add(tn, y, 0.2, pan)
        if role == 'groove' and ins:
            for h in (0, 1):
                idx = (b * 2 + h) % 8; tn = hum(t + h * (BEAT / 2 + SWING)); y = piano(upper[PAT8[idx]], 1.1, round(hv(VEL8[idx] * 0.7), 2))
                music.add(tn, y, 0.25, 0.1); mrev.add(tn, y, 0.15, 0.1)
        if role == 'sparse' and b in (0, 2):
            y = piano(upper[PAT8[(b * 2) % 8]], 0.9, round(hv(0.42), 2)); music.add(hum(t), y, 0.42, 0.1); mrev.add(t, y, 0.2, 0.1)
        if role != 'minor' and b in (0, 2):
            y = piano(root + 12, 1.1, round(hv(0.55, 0.08), 2), 0.5); music.add(hum(t, 4), y, 0.62, 0); mrev.add(t, y, 0.05, 0)
        if role == 'minor':
            if b == 0: y = lp(piano(root + 12, 2.8, 0.5, 0.4), 600); music.add(t, y, 0.8, 0)
            for q in range(4):
                y = hp(noise(int(0.04 * SR)), 6500) * expdec(int(0.04 * SR), 0.008) * hv(0.3 if q % 2 else 0.45, 0.2)
                music.add(hum(t + q * BEAT / 4, 3), lp(y, 9000, 1), 0.05, 0.3 if q % 2 else -0.2)
        if role in ('groove', 'arp') and not hb and not ins and b in (0, 2): music.add(t, kick(0.5), 0.5, 0)
        if role == 'arp':
            if b in (1, 3): music.add(t, P(nburst(0.06, 1400, 4200, 0.012, 0.5), thud(420, 0.02, 0.25, 0)), 0.26, 0.15)
            for q in range(4):
                tn = hum(t + q * BEAT / 4, 5); idx = (k * 4 + q) % 8
                y = lp(pluck(upper[[0, 1, 2, 3, 4, 3, 2, 1][idx]] + 12, 0.3, round(hv(0.35 if q == 0 else 0.25), 2), 0.7), 3200, 2)
                gg = 0.3 * phrase(tn) * (0.75 + 0.5 * HUM.random()); music.add(tn, y, gg, 0.4 * (1 if idx % 2 else -1)); mrev.add(tn, y, gg * 0.5, 0)
        if ins and b == 0 and bar_k % 2 == 0:
            for j, m in enumerate([root + 12] + notes[:4]):
                y = piano(m, 3.6, 0.32, 0.6); tj = t + j * 0.04; music.add(tj, y, 0.36, -0.2 + 0.1 * j); mrev.add(tj, y, 0.4, 0)

    tf = TOTAL - min(MU.get('final_chord_before_end', 9.0), 0.45 * TOTAL)      # 结尾：最后一个和弦，余音到片尾
    root, notes = MAJ[0]
    for j, m in enumerate([root - 12, root, root + 12, notes[1], notes[2], notes[2] + 5, notes[3], notes[4]]):
        y = piano(m, min(7.5, TOTAL - tf - 0.6), 0.42 if j < 2 else 0.34, 0.55); tj = tf + j * 0.045 + HUM.normal(0, 0.006); music.add(tj, y, 0.6, -0.35 + 0.08 * j); mrev.add(tj, y, 0.6, 0)
    for k, t in beats(END_FULL, tf - 0.2):
        if k % 2 == 0: y = piano(chord_at(t)[1][(k // 2) % 5] + 12, 1.4, 0.34, 0.7); music.add(hum(t), y, 0.42, 0.2); mrev.add(t, y, 0.5, 0)

    M = music.st() + 0.9 * reverb(mrev, 3.2, 11, 5000)
    secs = [(c['t0'], c['t1'], c['id']) for c in TL['chapters']]
    return {'stems': {'music': M}, 'ctx': ctx, 'sections': secs, 'kicks': []}
