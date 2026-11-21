"""正式档重影比对：python3 tools/ghostcheck.py [--format 名字] [--final 正式档] [--draft 草稿档] [--force] [--json 结果.json] [--outdir 图目录]
render.py --final 出完片后，体检（checkup.py）自动调用它；也可以单独跑。--final、--draft 不给时用 out/ 下这个画幅的正式档和草稿档。

为什么要比：正式档的运动模糊在快门内取若干子帧叠加。物体移动很快而子帧不够时，每个子帧各画出一份清晰的图像，
  一段字或一张卡片变成 2–6 份错开的副本（重影），读不出来。草稿档（同一条时间线，不开运动模糊）同一时刻是干净的。
  重影只在快速平移、滚动转场、横向滑入的那几帧出现，静帧自查和总览图都看不到，要逐帧比两档才找得到。
前提：两档来自同一份代码。草稿档和正式档的修改时间都要晚于 web/shots_*.js、project.json、timeline.json 里最新的那个，
  否则两档内容不一样，比出来全是误报：打印「草稿档早于当前代码，跳过比对」并跳过（不算错误）。--force 强制比。
判据：两档缩到长边 480 像素、每秒 30 帧，逐帧比较：
  正式档里出现、而草稿档同一位置（放宽 2 像素）没有的清晰边缘，占草稿档边缘数（至少按 200 算）的比例 > 0.23，
  「清晰」指近处梯度（隔 1 像素）不小于远处梯度（隔 3 像素）的一半：重影的副本是锐利的台阶，正确的运动模糊是宽的渐变带；
  连续 2 帧以上，而且画面在动（草稿档相邻帧的平均差 > 0.5 灰度级），报 ❌「正式档重影」。
  正常的运动模糊只会把边缘抹淡，不会在新的位置长出清楚的边缘，所以不会触发。
  护栏：候选前 1.5 秒或后 1.5 秒内的静止帧，至少一侧两档要对得上（灰度平均差中位数 ≤ 4）；两侧都对不上说明这一段两档内容不同，不报。
  只对画面在动的帧算边缘（静止帧不会有重影）：3 分钟的片子约 1 分钟比完。
输出：每处给时间段，和峰值那一帧的并排图（左正式档、右草稿档，原尺寸拼好后缩到宽 1600 以内），默认写到 frames/_view/ghost/。
怎么改：这一段运动太快，运动模糊的采样不够。调高 project.json 的 motion_blur.max（采样上限，默认 128），
  或用 FAST 登记这一段并给更大的采样数；也可以把这段运动放慢。改完用 render.py --final 起 止 重渲这几秒确认。
"""
import sys, json, time, queue, threading
from pathlib import Path
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
import numpy as np
from PIL import Image
from common import ROOT, pop_format, formats, out_name, decode, frame_at, probe

CMP_LONG, CMP_FPS = 480, 30        # 比对尺寸（长边）和帧率
EDGE_THR = 24                      # 边缘：横向加纵向的灰度差之和 > 24（0–255）
SHARP = 0.5                        # 清晰边缘：近处梯度 ≥ 远处梯度的一半（正确的运动模糊约 1/3，重影的副本接近 1）
NEW_EDGE = 0.23                    # 正式档的新边缘占草稿档边缘数的比例超过它算候选。标定：真重影最低约 0.24；画面很稀时，正确的运动模糊拖尾约 0.21
MOVING = 0.5                       # 草稿档相邻帧平均差（灰度级）超过它算画面在动
MIN_RUN = 2                        # 连续几帧才报
STALE_ERR, STALE_WIN = 4.0, 1.5    # 护栏：候选前或后 1.5 秒内的静止帧，至少一侧两档平均差的中位数 ≤ 4
MAX_IMAGES = 16


def code_mtime():
    """web/shots_*.js、project.json、timeline.json 里最新的修改时间"""
    fs = list((ROOT / 'web').glob('shots_*.js')) + [ROOT / n for n in ('project.json', 'timeline.json')]
    return max((f.stat().st_mtime for f in fs if f.exists()), default=0)


def _edges(f):
    """f: (n, h, w) int16 → 边缘 bool"""
    g = np.zeros(f.shape, bool)
    g[:, 1:-1, 1:-1] = (np.abs(f[:, 1:-1, 2:] - f[:, 1:-1, :-2]) + np.abs(f[:, 2:, 1:-1] - f[:, :-2, 1:-1])) > EDGE_THR
    return g


def _sharp_edges(f):
    """清晰的边缘：近处梯度（隔 1 像素）够大，且不小于远处梯度（隔 3 像素）的 SHARP 倍。
    重影的每一份副本都是锐利的台阶；正确的运动模糊是一条宽的渐变带，带里梯度也过阈值，但近处梯度只有远处的 1/3 左右"""
    g = np.zeros(f.shape, bool)
    g1 = np.abs(f[:, 3:-3, 4:-2] - f[:, 3:-3, 2:-4]) + np.abs(f[:, 4:-2, 3:-3] - f[:, 2:-4, 3:-3])
    g3 = np.abs(f[:, 3:-3, 6:] - f[:, 3:-3, :-6]) + np.abs(f[:, 6:, 3:-3] - f[:, :-6, 3:-3])
    g[:, 3:-3, 3:-3] = (g1 > EDGE_THR) & (g1 >= SHARP * g3)
    return g


def _new_edges(F, D):
    """正式档里出现、而草稿档同一位置（放宽 2 像素）没有的清晰边缘，占草稿档边缘数的比例。F, D: (n, h, w) int16"""
    from scipy.ndimage import binary_dilation
    cross = np.zeros((1, 3, 3), bool); cross[0, 1, :] = True; cross[0, :, 1] = True
    ef, ed = _sharp_edges(F), _edges(D)
    near = binary_dilation(ed, structure=cross, iterations=2)
    return (ef & ~near).reshape(len(F), -1).sum(1) / np.maximum(ed.reshape(len(D), -1).sum(1), 200)


def _threaded(gen):
    """解码放在线程里，两档同时解"""
    q = queue.Queue(maxsize=3)
    def run():
        try:
            for b in gen: q.put(b)
        finally: q.put(None)
    threading.Thread(target=run, daemon=True).start()
    while True:
        b = q.get()
        if b is None: return
        yield b


def _segments(mask, min_len):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]: j += 1
            if j - i >= min_len: out.append((i, j))
            i = j
        else: i += 1
    return out


def compare(final, draft, outdir, force=False, log=print):
    """返回 {status: ok|skipped, reason, found: [{t_start, t_end, peak_t, score, image}], ...}"""
    final, draft = Path(final), Path(draft)
    if not final.exists(): return {'status': 'skipped', 'reason': f'没有正式档 {final.name}'}
    if not draft.exists(): return {'status': 'skipped', 'reason': f'没有草稿档 {draft.name}，无从比对；需要时先渲草稿档（python3 tools/render.py）'}
    cm = code_mtime()
    if not force:
        if draft.stat().st_mtime < cm: return {'status': 'skipped', 'reason': '草稿档早于当前代码，跳过比对；需要时先重渲草稿档（python3 tools/render.py），再跑 python3 tools/ghostcheck.py'}
        if final.stat().st_mtime < cm: return {'status': 'skipped', 'reason': '正式档早于当前代码，跳过比对；先重渲正式档'}
    pf, pd = probe(final), probe(draft)
    if abs(pf['duration'] - pd['duration']) > 0.5:
        return {'status': 'skipped', 'reason': f'两档时长不同（正式档 {pf["duration"]:.1f} 秒，草稿档 {pd["duration"]:.1f} 秒），不是同一条时间线'}
    w, h = (CMP_LONG, round(CMP_LONG * pf['height'] / pf['width'])) if pf['width'] >= pf['height'] else (round(CMP_LONG * pf['width'] / pf['height']), CMP_LONG)
    T = time.time()
    motion, err, score = [], [], []
    prev = None
    for bf, bd in zip(_threaded(decode(final, w, h, CMP_FPS)), _threaded(decode(draft, w, h, CMP_FPS))):
        n = min(len(bf), len(bd)); F = bf[:n].astype(np.int16); D = bd[:n].astype(np.int16)
        Dp = np.concatenate([D[:1] if prev is None else prev[None], D[:-1]])
        mv = np.abs(D - Dp).mean((1, 2)); prev = D[-1]
        sc = np.zeros(n)
        idx = np.where(mv > MOVING)[0]
        if len(idx): sc[idx] = _new_edges(F[idx], D[idx])
        motion.append(mv); err.append(np.abs(F - D).mean((1, 2))); score.append(sc)
    if not motion: return {'status': 'skipped', 'reason': '解码失败，没有读到画面'}
    motion, err, score = np.concatenate(motion), np.concatenate(err), np.concatenate(score)
    n = len(motion); win = int(STALE_WIN * CMP_FPS)
    found, stale = [], []
    for a, b in _segments((score > NEW_EDGE) & (motion > MOVING), MIN_RUN):
        side = [[i for i in rg if motion[i] < 0.3] for rg in (range(max(0, a - win), a), range(b, min(n, b + win)))]
        side = [float(np.median(err[x])) for x in side if x]
        if side and min(side) > STALE_ERR: stale.append(round(a / CMP_FPS, 2)); continue     # 前后两侧的静止帧都对不上：这一段两档内容不同
        m = a + int(np.argmax(score[a:b]))
        found.append({'t_start': round(a / CMP_FPS, 2), 't_end': round(b / CMP_FPS, 2), 'peak_t': round(m / CMP_FPS, 2), 'score': round(float(score[m]), 3)})
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    for f in outdir.glob('ghost_*.jpg'): f.unlink()
    for k, g in enumerate(found[:MAX_IMAGES]):
        fa = frame_at(final, g['peak_t'])
        da = frame_at(draft, g['peak_t'], size=fa.size) if fa else None
        if fa is None or da is None: continue
        cv = Image.new('RGB', (fa.width * 2 + 12, fa.height), 'white'); cv.paste(fa, (0, 0)); cv.paste(da, (fa.width + 12, 0))
        cv.thumbnail((1600, 1600), Image.LANCZOS)
        p = outdir / f'ghost_{k + 1}.jpg'; cv.save(p, quality=85); g['image'] = str(p)
    return {'status': 'ok', 'final': str(final), 'draft': str(draft), 'forced': force, 'frames': int(n), 'compared': int((motion > MOVING).sum()),
            'elapsed': round(time.time() - T, 1), 'found': found, 'stale': stale, 'score_p99': round(float(np.percentile(score, 99)), 3)}


def summary(res):
    """终端用的几行"""
    if res['status'] != 'ok': return [f"[重影比对] {res['reason']}"]
    f = res['found']
    L = [f"[重影比对] 比了 {res['frames']} 帧（画面在动的 {res['compared']} 帧），用时 {res['elapsed']:.0f} 秒：" +
         (f"❌ {len(f)} 处正式档重影" if f else '没有重影') + ('（--force 强制比对）' if res.get('forced') else '')]
    for g in f:
        L.append(f"  {g['t_start']:.2f}–{g['t_end']:.2f}s（峰值 {g['peak_t']:.2f}s，新边缘占比 {g['score']:.2f}）" + (f"　图：{g['image']}（左正式档、右草稿档）" if g.get('image') else ''))
    if f: L.append('  这几段运动太快、运动模糊的采样不够：调高 project.json 的 motion_blur.max，或用 FAST 登记这一段并给更大的采样数，也可以放慢这段运动')
    if res['stale']: L.append(f"  另有 {len(res['stale'])} 段两档的静止画面对不上（两档内容不同），没有报：{res['stale'][:8]}")
    return L


def main():
    argv = sys.argv[1:]
    fmt = pop_format(argv)[0]
    def opt(n):
        if n in argv: i = argv.index(n); v = argv[i + 1]; del argv[i:i + 2]; return v
        return None
    final, draft, jp, outdir = opt('--final'), opt('--draft'), opt('--json'), opt('--outdir')
    force = '--force' in argv
    if force: argv.remove('--force')
    if argv: sys.exit(f'看不懂参数：{" ".join(argv)}（python3 tools/ghostcheck.py --help 看用法）')
    final = final or ROOT / 'out' / out_name(fmt)
    draft = draft or ROOT / 'out' / out_name(fmt, '_draft')
    outdir = outdir or ROOT / 'frames' / '_view' / ('ghost' + (f'_{fmt}' if len(formats()) > 1 else ''))
    res = compare(final, draft, outdir, force)
    if jp: json.dump(res, open(jp, 'w'), ensure_ascii=False, indent=1)
    print('\n'.join(summary(res)))


if __name__ == '__main__':
    main()
