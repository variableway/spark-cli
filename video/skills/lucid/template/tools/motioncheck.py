"""静止段、时长、抖动检查：python3 tools/motioncheck.py [成片.mp4] [--track 登记.json] [--target 秒] [--max-still 秒] [--json 输出路径]
不给成片路径时读 out/ 下的正式档，没有就读草稿档；--track 默认找 render.py 渲这支成片时存的 out/segments/full_<画幅>_<档>_track.json；
--target 默认读 project.json 的 target_sec。会被 checkup.py 调用，也可以单独跑。
- 静止段：每 0.125 秒取一帧（128 像素宽灰度），和 0.5 秒前比，明显变化（灰度差 > 6）的像素不到 2.5% 算「静止」（只有字幕、进度条这类小块在变也算静止）。
  连续静止超过 --max-still（讲解片默认 3 秒，宣传片 2 秒）报 ℹ️（可选提示），给出起止时刻。片尾最后 2 秒的停留不算。
  这是提示：停住是为了让观众读完、消化，就保留；内容在空等，就让内容推进。不要为了过检查加无意义的动作。
- 时长：成片时长和目标差超过 10% 是 ❌（短了就加内容、放慢讲解，长了就删减），改完重渲再查。
- 抖动：只量镜头，不看像素。渲染时每帧记下引擎登记的 window.__CAMS（每个镜头 cam() 相对 screen() 的变换）和 window.__GLOBAL（转场位移 + SHAKES 震动），
  取画面上 5 个参考点（中心和四个 1/4 点），算相邻两帧之间镜头变换让它们移动了多少：平移（x、y）、缩放（径向）、旋转（切向）四个分量，
  速度按 30 帧/秒折算成「像素/帧」。角色的压扁拉伸、局部旋转、粒子都不在镜头矩阵里，不参与。
  反向：同一分量相邻两帧速度方向相反，且两帧都 ≥ 0.5 像素/帧（更慢的来回看不出来，不计）。
  快抖：1 秒里反向 ≥ 6 次，在「稳」镜头里是 ⚠️（硬伤，看洋葱皮决定）。慢晃：平滑 0.25 秒后的速度在 5 秒里反向 ≥ 4 次（浮动周期短于 2.5 秒），只报 ℹ️：
  弹簧推拉的回弹、来回摇的镜头也会这样，是不是晃，看洋葱皮图判断。判定窗口按镜头切开。
  标了 motion: "可以震" 的镜头里的抖动是 ℹ️。SHAKES 登记的震动（只在「可以震」镜头里生效）不算抖动；
  「可以震」镜头里单次连续快抖（反向间隔 ≤ 3 帧、≥ 3 次）超过 0.5 秒报 ℹ️：震屏通常要短促。
  标「可以震」的镜头超过三分之一也是 ℹ️ 提示。
- 空帧（empty_frames，checkup.py 调用）：全片每个像素的中位数作背景板；偏离背景板的像素 < 1.5%，且偏离这一帧主背景色（四边像素中位色）的像素 < 4%，
  持续 ≥ 0.3 秒（片头片尾各 0.5 秒不查），报 ⚠️。画面上只剩一张卡片或一根箭头，多半是上一组退完、下一组还没进来。
  整屏色块（去掉四边 8% 后几乎没有边缘，不是黑场）持续 ≥ 0.3 秒也报 ⚠️：满屏一块颜色或渐变、上面没有东西，多半是转场色块停住了。
"""
import sys, json, math, subprocess
import numpy as np
from pathlib import Path

LAG, FPS_S, PIX_T, SHARE_T = 0.5, 8, 6, 0.025
JIT_N = 6          # 快抖：1 秒里反向次数
SWAY_N = 4         # 慢晃：5 秒里反向次数
V_MIN = 0.5        # 像素/帧（按 30 帧/秒折算）：更慢的反向不计
BURST_MAX = 0.5    # 「可以震」镜头里单次快抖最长 0.5 秒


def _ff():
    try:
        sys.path.insert(0, str(Path(__file__).parent)); from common import ffmpeg; return ffmpeg()
    except Exception: return 'ffmpeg'


FF = _ff()


def probe(path):
    """只用 ffmpeg（不依赖 ffprobe）读时长和画幅。"""
    import re
    e = subprocess.run([FF, '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
    h, m, sec = re.search(r'Duration: (\d+):(\d+):([\d.]+)', e).groups()
    w, hh = map(int, re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', e).groups())
    return int(h) * 3600 + int(m) * 60 + float(sec), w, hh


def stills(path, w, h, ff=None):
    ff = ff or FF
    sw = 128; sh = max(2, round(sw * h / w / 2) * 2)
    raw = subprocess.run([ff, '-loglevel', 'error', '-i', str(path), '-vf', f'fps={FPS_S},scale={sw}:{sh}:flags=area,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    n = sw * sh
    f = np.frombuffer(raw[:len(raw) // n * n], np.uint8).reshape(-1, sh, sw).astype(np.int16)
    k = int(LAG * FPS_S)
    share = np.array([0.0] * k + [float((np.abs(f[i] - f[i - k]) > PIX_T).mean()) for i in range(k, len(f))])
    share[:k] = 1.0                                     # 开头半秒不判
    return share


REF = [(0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]


def _m(v):
    """[a,b,c,d,e,f] → 3×3"""
    if not v: return np.eye(3)
    a, b, c, d, e, f = v; return np.array([[a, c, e], [b, d, f], [0, 0, 1.0]])


def _vel(M0, M1, W, H):
    """两帧变换之间参考点的位移：(平移 x, 平移 y, 径向, 切向)，像素"""
    q = np.array([[x * W, y * H, 1.0] for x, y in REF]).T
    try: p = np.linalg.solve(M0, q)
    except np.linalg.LinAlgError: return np.zeros(4)
    d = (M1 @ p - q)[:2].T; mx, my = d.mean(0)
    r = q[:2].T[1:] - (W / 2, H / 2); u = r / np.linalg.norm(r, axis=1)[:, None]; rest = d[1:] - (mx, my)
    return np.array([mx, my, float((rest * u).sum(1).mean()), float((rest[:, 1] * u[:, 0] - rest[:, 0] * u[:, 1]).mean())])


def track_motion(track, shots, U=1.0):
    """track：render.py 存的登记（fps、size、frames [[t, 在画的镜头, {镜头: cam}, global]]、shakes）。shots = [(id, t0, t1, 标签)]。
    返回 (抖动段 [起, 止, 反向次数, 镜头, 种类], 单次太长的快抖 [起, 止, 镜头], 有没有镜头登记)。"""
    fps = track['fps']; W, H = track['size']; k30 = fps / 30.0
    fr = sorted(track['frames'], key=lambda r: r[0])
    lab = {i: g for i, a, b, g in shots}
    has = any(r[2] or r[3] for r in fr)
    # SHAKES 登记的震动：从 t0 起到幅度低于 0.5 像素为止，只在「可以震」镜头里生效
    sh_win = []
    for t0, amp, tau in [x[:3] for x in (track.get('shakes') or [])]:
        sid = next((i for i, a, b, g in shots if a - 1e-6 <= t0 < b), None)
        if sid and lab.get(sid) == '可以震' and amp * U > 0.5: sh_win.append((t0, t0 + tau * math.log(amp * U / 0.5)))
    series = {}                                                     # 镜头 → [(t, cam 分量 4, global 分量 4)]
    for r0, r1 in zip(fr, fr[1:]):
        if abs(r1[0] - r0[0] - 1 / fps) > 0.5 / fps: continue
        live = set(r0[1] or []) & set(r1[1] or []) if r0[1] is not None and r1[1] is not None else \
            {i for i, a, b, g in shots if a <= r1[0] < b}
        gv = _vel(_m(r0[3]), _m(r1[3]), W, H) * k30
        for sid in live:
            cv = _vel(_m((r0[2] or {}).get(sid)), _m((r1[2] or {}).get(sid)), W, H) * k30
            series.setdefault(sid, []).append((r1[0], cv, gv))
    bad, long_b = [], []
    def put(sid, a0, b0, n, kind):
        if bad and bad[-1][3] == sid and bad[-1][4] == kind and bad[-1][1] >= a0 - 1e-6: bad[-1][1] = max(bad[-1][1], b0); bad[-1][2] = max(bad[-1][2], n)
        else: bad.append([a0, b0, n, sid, kind])
    for sid, rows in series.items():
        ts = np.array([x[0] for x in rows]); V = np.array([np.r_[x[1], x[2]] for x in rows])     # N × 8
        in_shake = np.array([any(a <= t <= b for a, b in sh_win) for t in ts])
        rev = np.zeros(len(ts)); rev_all = np.zeros(len(ts))
        for j in range(8):
            v = V[:, j]; m = (np.abs(v[1:]) >= V_MIN) & (np.abs(v[:-1]) >= V_MIN) & (np.sign(v[1:]) != np.sign(v[:-1]))
            rev_all[1:] += m
            rev[1:] += m & ~in_shake[1:] if j >= 4 else m
        n = len(ts); win = int(round(fps))
        starts = range(0, max(1, n - win + 1), win) if n > win else [0]
        for s0 in starts:                                           # 快抖
            c = int(rev[s0:s0 + win].sum())
            if c >= JIT_N: put(sid, round(ts[s0] - 1 / fps, 2), round(ts[min(n, s0 + win) - 1], 2), c, '快抖')
        ks = max(1, int(round(0.25 * fps)) | 1)                     # 慢晃
        for j in range(8):
            v = V[:, j].copy()
            if j >= 4: v[in_shake] = 0
            vs = np.convolve(v, np.ones(ks) / ks, 'same')
            sg = [(i, np.sign(x)) for i, x in enumerate(vs) if abs(x) >= V_MIN]
            rv = [sg[i][0] for i in range(1, len(sg)) if sg[i][1] != sg[i - 1][1]]
            w5 = 5 * win
            for s0 in (range(0, n - w5 + 1, win) if n > w5 else [0]):
                ins = [r for r in rv if s0 <= r < s0 + w5]
                if len(ins) >= SWAY_N: put(sid, round(ts[ins[0]], 2), round(ts[ins[-1]], 2), len(ins), '慢晃')
        if lab.get(sid) == '可以震':                                # 单次快抖的长度
            idx = np.nonzero(rev_all)[0]; bursts = []
            for i in idx:
                if bursts and i - bursts[-1][1] <= 3: bursts[-1][1] = i; bursts[-1][2] += 1
                else: bursts.append([i, i, 1])
            for i0, i1, c in bursts:
                if c >= 3 and ts[i1] - ts[i0] + 1 / fps > BURST_MAX: long_b.append([round(ts[i0] - 1 / fps, 2), round(ts[i1], 2), sid])
    bad.sort()
    return bad, long_b, has


def runs(share, max_still, dur):
    out, s0 = [], None
    for i, v in enumerate(list(share < SHARE_T) + [False]):
        if v and s0 is None: s0 = i
        if not v and s0 is not None:
            a = max(0.0, s0 / FPS_S - LAG); b = min(dur, i / FPS_S)  # 静止从比较起点算起
            if b - a > max_still and a < dur - 2.0: out.append((round(a, 1), round(min(b, dur), 1), round(b - a, 1)))
            s0 = None
    return out


def check(path, target=None, max_still=3.0, ff=None, shots=None, track=None, U=1.0):
    """track：render.py 存的登记（dict）；没有时只查静止段和时长，抖动报「查不了」。"""
    dur, w, h = probe(path)
    share = stills(path, w, h, ff)
    st = runs(share, max_still, dur)
    shots = shots or []                                    # [(id, t0, t1, 标签)]
    lab = {i: g for i, a, b, g in shots}
    jr, long_b, has = [], [], False
    if track:
        jb, lb, has = track_motion(track, shots, U)
        jr = [dict(a=a, b=b, n=n, shot=sid, kind=k, tag=lab.get(sid, '稳')) for a, b, n, sid, k in jb]
        long_b = [dict(a=a, b=b, shot=sid) for a, b, sid in lb]
    res = {'jitter': jr, 'shake_long': long_b, 'shake_shots': [i for i, a, b, g in shots if g == '可以震'], 'n_shots': len(shots),
           'track': bool(track), 'track_has_cams': has, 'video': str(path), 'duration': round(dur, 2), 'max_still': max_still, 'still_runs': st,
           'still_total': round(sum(r[2] for r in st), 1), 'static_share': round(float((share < SHARE_T).mean()), 2), 'target': target}
    if target:
        res['duration_off'] = round((dur - target) / target, 3)
        res['duration_ok'] = abs(dur - target) <= 0.10 * target
    return res


# ---------------------------------------------------------------- 空帧
EMPTY_DEV, EMPTY_PLATE, EMPTY_BG, EMPTY_MIN, EMPTY_EDGE, EMPTY_FPS = 28, 0.015, 0.04, 0.3, 0.5, 10
WASH_EDGE, WASH_SHARE, WASH_DARK, WASH_MARGIN = 10, 0.004, 24, 0.08   # 整屏色块：去掉四边 8% 后，相邻像素亮度差 > 10 的像素 < 0.4%；中位色很暗（各通道 < 24）的算黑场，不报


def empty_frames(path):
    """空帧：取全片每个像素的中位数作背景板（每秒一帧，静止的纹理底、网格也算背景）。
    偏离背景板的像素 < 1.5%、偏离这一帧主背景色的像素 < 4%，持续 ≥ 0.3 秒（片头片尾 0.5 秒不查）。
    另查整屏色块：去掉四边 8%（画框、描边）后几乎没有边缘（相邻像素亮度差 > 10 的像素 < 0.4%），颜色不是黑场，同样持续 ≥ 0.3 秒。
    满屏一块颜色或渐变、上面没有任何东西，多半是转场色块停住了。返回 [(起, 止, 最低内容占比, 种类)]，种类是「只剩背景」或「整屏色块」"""
    from common import probe, decode
    info = probe(path); W_, H_ = info['width'], info['height']
    w, h = (480, round(480 * H_ / W_)) if W_ >= H_ else (round(480 * W_ / H_), 480)
    plate = np.median(np.concatenate(list(decode(path, w, h, fps=1, gray=False))), axis=0).astype(np.int16)   # 背景板：每秒一帧的逐像素中位数
    cov, cov_bg, solid = [], [], []
    for b in decode(path, w, h, fps=EMPTY_FPS, gray=False):
        bt = b.astype(np.int16)
        my, mx = int(bt.shape[1] * WASH_MARGIN), int(bt.shape[2] * WASH_MARGIN)
        g = bt[:, my:bt.shape[1] - my, mx:bt.shape[2] - mx].mean(-1)
        ed = np.maximum(np.abs(np.diff(g, axis=2))[:, :-1, :], np.abs(np.diff(g, axis=1))[:, :, :-1]) > WASH_EDGE
        med = np.median(bt.reshape(len(bt), -1, 3), axis=1)            # 这一帧的中位色：很暗的是黑场，不算
        solid.extend(((ed.reshape(len(bt), -1).mean(1) < WASH_SHARE) & (med.max(1) >= WASH_DARK)).tolist())
        cov.extend((np.abs(bt - plate).max(-1) > EMPTY_DEV).reshape(len(bt), -1).mean(1).tolist())
        border = np.concatenate([bt[:, :4].reshape(len(bt), -1, 3), bt[:, -4:].reshape(len(bt), -1, 3),
                                 bt[:, :, :4].reshape(len(bt), -1, 3), bt[:, :, -4:].reshape(len(bt), -1, 3)], 1)
        bgc = np.median(border, axis=1)[:, None, None, :]          # 主背景色：四边像素的中位色（静止的版面算内容，低对比的纹理底大多不算）
        cov_bg.extend((np.abs(bt - bgc).max(-1) > EMPTY_DEV).reshape(len(bt), -1).mean(1).tolist())
    cov, cov_bg, solid = np.array(cov), np.array(cov_bg), np.array(solid, bool)
    bgm = (cov < EMPTY_PLATE) & (cov_bg < EMPTY_BG); e = int(EMPTY_EDGE * EMPTY_FPS)
    mask = bgm | solid
    mask[:e] = False; mask[-e:] = False
    out, i = [], 0
    while i < len(mask):
        if not mask[i]: i += 1; continue
        j = i
        while j < len(mask) and mask[j]: j += 1
        if (j - i) / EMPTY_FPS >= EMPTY_MIN:
            kind = '整屏色块' if solid[i:j].mean() > 0.5 else '只剩背景'
            out.append((round(i / EMPTY_FPS, 2), round(j / EMPTY_FPS, 2), round(float(cov[i:j].min()), 4), kind))
        i = j
    return out


def lines(res):
    L = []
    st = res['still_runs']
    L.append(('ℹ️' if st else '✅', f'静止段（>{res["max_still"]:g} 秒画面几乎不动）',
              (f'{len(st)} 处，合计 {res["still_total"]} 秒：' + '，'.join(f'{a}–{b}s（{d}s）' for a, b, d in st[:15]) + (' …' if len(st) > 15 else '')
               + '。这段画面停住了：如果是让观众读完或消化，可以保留；如果是内容在空等，就让内容推进') if st else '没有'))
    jr = res.get('jitter') or []
    hard = [r for r in jr if r['tag'] == '稳' and r['kind'] == '快抖']; soft = [r for r in jr if r not in hard]   # 慢晃多半是设计出来的推拉回弹，只提示
    fmt = lambda rs: '，'.join(f"{r['a']:g}–{r['b']:g}s {r['shot']}「{r['tag']}」{r['kind']}（镜头反向 {r['n']} 次）" for r in rs[:12])
    if not res.get('track') or not res.get('track_has_cams'):
        L.append(('ℹ️', '画面抖动', '查不了：' + ('没有渲染时的登记（用 render.py 渲一次就有）' if not res.get('track') else '引擎没有登记镜头矩阵（window.__CAMS / __GLOBAL）')))
    else:
        L.append(('⚠️' if hard else '✅', '画面抖动（「稳」镜头）', (f'{len(hard)} 段：' + fmt(hard) + '。只量镜头（cam 和全局变换），角色自己的动作不算。「稳」镜头的镜头运动要慢而顺（drift、camKeys、springTo）；确实是撞击、爆点，就把这个镜头标成 motion: "可以震"，用 SHAKES 登记') if hard else '没有（只量镜头 cam 和全局变换）'))
        if soft: L.append(('ℹ️', '画面抖动（「可以震」镜头，看一眼）', f'{len(soft)} 段：' + fmt(soft) + '。确认是有意的震屏'))
    ss, n = res.get('shake_shots') or [], res.get('n_shots') or 0
    if ss or n:
        over = n and len(ss) > n / 3
        L.append(('ℹ️', '标了「可以震」的镜头', f'{len(ss)}/{n} 个：{", ".join(ss) or "没有"}' + ('。超过三分之一：震屏只给撞击、惊喜、重拍这类瞬间，其余镜头确认是不是该改回「稳」' if over else '')))
    lb = res.get('shake_long') or []
    if lb: L.append(('ℹ️', '单次震动太长', f'{len(lb)} 次超过 {BURST_MAX} 秒：' + '，'.join(f"{r['a']:g}–{r['b']:g}s {r['shot']}" for r in lb[:10]) + '。震屏要短促，0.5 秒内衰减完'))
    if res.get('target'):
        off = res['duration_off']
        lv = '❌' if not res['duration_ok'] else ('⚠️' if abs(off) > 0.05 else '✅')
        L.append((lv, '时长对目标',
                  f'成片 {res["duration"]} 秒，目标 {res["target"]:g} 秒，差 {off * 100:+.0f}%' + ('' if lv == '✅' else ('（超过 ±10%，必改）：' if lv == '❌' else '（5–10%，能补就补）：') + ('加内容或放慢，补足各段秒数后重渲' if off < 0 else '删减后重渲'))))
    else:
        L.append(('ℹ️', '时长对目标', f'成片 {res["duration"]} 秒；project.json 没写 target_sec，查不了。用户说了时长就写进去'))
    return L


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] in ('-h', '--help'): print(__doc__); sys.exit(0)
    def opt(k, d=None):
        if k in a: i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
        return d
    target = opt('--target'); ms = opt('--max-still'); jo = opt('--json')
    cfg = {}
    if a:
        path = Path(a[0])
        pj = Path('project.json')
        if pj.exists(): cfg = json.load(open(pj))
    else:
        sys.path.insert(0, str(Path(__file__).parent)); from common import ROOT, project, out_name, formats
        cfg = project(); f0 = next(iter(formats(cfg))); path = ROOT / 'out' / out_name(f0)
        if not path.exists() and (ROOT / 'out' / out_name(f0, '_draft')).exists(): path = ROOT / 'out' / out_name(f0, '_draft')
    if target is None and cfg.get('target_sec'): target = cfg['target_sec']
    genre = cfg.get('genre', 'explainer')
    tlp = (Path('timeline.json') if a else ROOT / 'timeline.json')
    shots = []
    if tlp.exists():
        sc = json.load(open(tlp, encoding='utf-8'))['scenes'].values()
        shots = [(x['id'], x['t0'], x['t1'], x.get('motion', '稳')) for x in sorted(sc, key=lambda x: x['t0'])]
    tk = opt('--track')
    if tk is None:                                         # render.py 渲这支成片时存的登记
        seg = path.parent / 'segments'; f0 = next(iter(json.load(open('project.json')).get('formats') or {'main': 0})) if a else f0
        cand = seg / f"full_{f0}_{'draft' if path.stem.endswith('_draft') else 'final'}_track.json"
        tk = str(cand) if cand.exists() else None
    track = json.load(open(tk)) if tk else None
    U = min(track['size']) / 1080 if track else 1.0
    res = check(path, float(target) if target else None, float(ms) if ms else (2.0 if genre == 'promo' else 3.0), shots=shots, track=track, U=U)
    for lv, n, note in lines(res): print(f'{lv} {n}：{note}')
    if jo: json.dump(res, open(jo, 'w'), ensure_ascii=False, indent=1)
    sys.exit(1 if any(l[0] == '❌' for l in lines(res)) else 0)
