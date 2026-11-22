"""成片体检：python3 tools/review.py [视频路径] [--format 名字] [--genre promo|explainer]
render.py 渲完会经 checkup.py 自动调用它；不给视频路径时读 out/ 下的正式档，没有就读草稿档。
看不到动态、听不到声音，就用数字和总览图代替眼睛和耳朵。输出：
  frames/_view/review_NN.jpg   每 0.5 秒一帧的总览（带时间和拍号），必须看
  out/review.json              全部指标
  frames/_view/blank_<秒>s.jpg 报了拍点空画面时：拍点前 0.2 秒到后 0.3 秒的逐帧条（拍点那一帧红框，空的帧标「空」）
  终端里一张对照质量线的表：✅ 达标 / ⚠️ 要看 / ❌ 要改；ℹ️ 是只供参考的数字，不算不达标
护栏只有观众看得见、听得见的硬伤：单帧跳变、拍点空画面（同一帧只报一次）、响度、真峰值。其余指标（最长低变化段、结尾停留、整帧被闪光刷灰等）
只作参考（ℹ️）：画面停多久、结尾留多久是设计选择。
指标说明见 references/review.md。阈值来自 X 上热门作品的测量范围，不是拍脑袋。
"""
import sys, json, re, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from common import ROOT, ffmpeg, project, timeline, pop_format, out_name

ARGV = sys.argv[1:]
FMT = pop_format(ARGV)[0]
GENRE = None
if '--genre' in ARGV: i = ARGV.index('--genre'); GENRE = ARGV[i + 1]; del ARGV[i:i + 2]
CFG = project()
V = ARGV[0] if ARGV else str(ROOT / 'out' / out_name(FMT))
if not ARGV and not Path(V).exists():                       # 只渲了草稿档时，体检草稿档并说明
    _pv = Path(V).with_name(Path(V).stem + '_draft.mp4')
    if _pv.exists(): print(f'没有正式档 {Path(V).name}，体检草稿档 {_pv.name}（半尺寸、最高 30 帧/秒、无运动模糊，数字仅供参考）'); V = str(_pv)
    else: sys.exit(f'找不到成片 {V}：先运行 python3 tools/render.py（草稿档）或 --final（正式档），或把视频路径作为参数传进来')
FF = ffmpeg()
try:
    TL = timeline()
except Exception:
    TL = None
GENRE = GENRE or CFG.get('genre') or ('explainer' if (TL or {}).get('mode') == 'voice' else 'promo')

# 质量线：promo = 无旁白、靠音乐和剪辑的短片；explainer = 有配音的讲解片
# 「新内容」= 相隔 0.5 秒的两帧（64 像素宽、模糊后）的平均灰度差，不受颗粒噪声和极慢推镜影响。
# 宣传片阈值的依据：7 支热门原片的新内容中位数 1.4–24，最长低变化段 0–4 秒，画面占用率 0.07–0.27，响度 -12 ~ -14.5 LUFS；
# 一支被判为「中段静止约 4 秒」的失败样本：中位数 0.19，最长低变化段 3.6 秒，占用率 0.03。
# 每项 (下限, 上限, 是不是护栏)。护栏没达标算 ⚠️/❌；不是护栏的只打印参考。
BAR = {
    'promo': {'novelty_median': (1.0, None, False), 'low_share': (None, 0.3, False), 'longest_low': (None, 2.0, False), 'end_hold': (None, 3.0, False),
              'fill_mean': (0.06, None, False), 'loudness': (-16.0, -12.0, True), 'true_peak': (None, -0.5, True),
              'pops': (None, 0, True), 'blank_beats': (None, 0, True), 'washes': (None, 0, False)},
    'explainer': {'novelty_median': (0.3, None, False), 'low_share': (None, 0.8, False), 'longest_low': (None, 10.0, False), 'end_hold': (None, 7.0, False),
                  'fill_mean': (0.05, None, False), 'loudness': (-18.0, -14.0, True), 'true_peak': (None, -0.5, True),
                  'pops': (None, 0, True), 'blank_beats': (None, 0, True), 'washes': (None, 0, False)},
}[GENRE]
# 讲解片阈值的依据：两支已交付的配音讲解片（5–10 分钟）新内容中位数 0.35、0.61，低变化占比 0.61–0.73，最长低变化段约 12 秒（引语页），结尾约 6 秒。
LAG, NFPS, LOW = 0.5, 10, 1.0


def probe(path):
    s = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    d = re.search(r'Duration: (\d+):(\d+):([\d.]+)', s); dur = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))
    v = re.search(r'Video: .*?(\d{2,5})x(\d{2,5}).*?([\d.]+) fps', s)
    return dict(duration=round(dur, 3), width=int(v.group(1)), height=int(v.group(2)), fps=float(v.group(3)), audio='Audio:' in s)


def grey_frames(path, w, h, size=160):
    sw, sh = (size, max(2, round(size * h / w / 2) * 2)) if w >= h else (max(2, round(size * w / h / 2) * 2), size)
    p = subprocess.Popen([FF, '-loglevel', 'error', '-i', path, '-vf', f'scale={sw}:{sh}:flags=area,format=gray', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    n = sw * sh; out = []
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        out.append(np.frombuffer(b, np.uint8).reshape(sh, sw).astype(np.float32))
    p.wait(); return out


def rgb_frames(path, w, h, step, tw=320):
    th = round(tw * h / w) if w >= h else 320; tw2 = tw if w >= h else round(320 * w / h)
    p = subprocess.run([FF, '-loglevel', 'error', '-i', path, '-vf', f'fps=1/{step}:round=up,scale={tw2}:{th}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True)
    n = tw2 * th * 3
    return [np.frombuffer(p.stdout[i:i + n], np.uint8).reshape(th, tw2, 3) for i in range(0, len(p.stdout) - n + 1, n)], (tw2, th)


def fill_ratio(im):
    """画面占用率：与这一帧底色差别明显的像素占比（参考值）。底色取量化后最多的那一格里像素的平均色，
    先做 3×3 模糊去掉颗粒，阈值 16：浅底上的白色组件（差约 20–30）也算内容。"""
    from scipy.ndimage import uniform_filter
    f = uniform_filter(im.astype(np.float32), size=(3, 3, 1))
    q = (f // 24).reshape(-1, 3).astype(np.int32); keys = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    vals, cnt = np.unique(keys, return_counts=True); bg = f.reshape(-1, 3)[keys == vals[cnt.argmax()]].mean(0)
    return float((np.abs(f - bg).max(-1) > 16).mean())


def edge_share(g):
    """这一帧有没有东西：模糊后灰度梯度明显的像素占比。纯色、渐变、暗角、颗粒都接近 0；画面上只有一个小圆点也在 0.001 以上。"""
    from scipy.ndimage import gaussian_filter, sobel
    b = gaussian_filter(g, 0.8)
    return float((np.hypot(sobel(b, 0), sobel(b, 1)) > 40).mean())


def beat_points(fps):
    """要检查是不是空画面的帧：每个镜头的起点，节拍时间轴再加每个半拍；music.sections 里的 gap 段除外（空拍本来就该空）。
    用未舍入的时刻和 1e-3 秒容差比较 gap 的起止：gap 起点那一拍也排除，gap 终点那一拍照常检查。
    先把时刻换算成帧号再去重：镜头起点和半拍常常落在同一帧（时间轴里的秒数只差舍入误差），同一帧只查一次、只报一次。
    返回 [(帧号, 镜头起点的镜头 id 或 None)]，按帧号排序。"""
    if not TL: return []
    pts = [(s['t0'], s['id']) for s in TL['scenes'].values()]
    off, beat = TL.get('offset', 0), TL.get('beat')
    if TL.get('mode') in ('beats', 'manual') and beat:
        k = 0
        while off + k * beat / 2 < TL['total'] - 1e-6: pts.append((off + k * beat / 2, None)); k += 1
    gaps = [(off + s['from'] * beat, off + s['to'] * beat) for s in (CFG.get('music') or {}).get('sections', []) if s.get('type') == 'gap' and beat]
    out = {}
    for t, sid in pts:
        if any(a - 1e-3 <= t < z - 1e-3 for a, z in gaps): continue
        i = int(round(t * fps))
        out[i] = out.get(i) or sid
    return sorted(out.items())


BLANK = 0.0005                                              # edge_share 低于它算空画面
STRIP_PRE, STRIP_POST = 0.2, 0.3                            # 拍点空画面的逐帧条：拍点前 0.2 秒到后 0.3 秒


def blank_strip(path, info, g, i, sid):
    """拍点空画面：拍点前 0.2 秒到后 0.3 秒逐帧拼成条图（拍点那一帧红框，空的帧标「空」）。返回 (图路径, 拍点附近连续空帧的 [起, 止] 秒, 空帧数)"""
    from common import font
    fps = info['fps']; n = len(g)
    i0, i1 = max(0, i - round(STRIP_PRE * fps)), min(n - 1, i + round(STRIP_POST * fps))
    empty = [edge_share(g[k]) < BLANK for k in range(i0, i1 + 1)]
    a = b = i                                                # 拍点所在的那一段连续空帧
    while a - 1 >= 0 and edge_share(g[a - 1]) < BLANK and i - a < 3 * fps: a -= 1
    while b + 1 < n and edge_share(g[b + 1]) < BLANK and b - i < 3 * fps: b += 1
    W_, H_ = info['width'], info['height']
    cw = 194 if W_ >= H_ else 120; ch = round(cw * H_ / W_ / 2) * 2; cols = 8 if W_ >= H_ else 10      # 宽不超过 1600
    m = i1 - i0 + 1
    # 定位到第 i0 帧：-ss 取帧号前半帧，passthrough 不补重复帧（默认的恒定帧率输出会把第一帧重复一次，整条错开一帧）
    r = subprocess.run([FF, '-loglevel', 'error', '-ss', f'{max(0.0, (i0 - 0.5) / fps):.4f}', '-i', path, '-fps_mode', 'passthrough', '-frames:v', str(m),
                        '-vf', f'scale={cw}:{ch}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    ims = [np.frombuffer(r[k:k + cw * ch * 3], np.uint8).reshape(ch, cw, 3) for k in range(0, len(r) - cw * ch * 3 + 1, cw * ch * 3)]
    rows = (len(ims) + cols - 1) // cols; top, lab = 26, 18
    sh = Image.new('RGB', (cols * (cw + 4) + 4, top + rows * (ch + lab + 4)), (30, 30, 30)); d = ImageDraw.Draw(sh); f = font(13)
    d.text((6, 5), f'{i / fps:.2f}s ' + (f'cut > {sid}' if sid else 'half-beat') + f'  frames {i0}–{i1} ({fps:g} fps)   red = beat frame   空 = nothing on screen', fill=(120, 220, 255), font=f)
    for k, im in enumerate(ims):
        x, y = 4 + (k % cols) * (cw + 4), top + (k // cols) * (ch + lab + 4); fi = i0 + k
        sh.paste(Image.fromarray(im), (x, y))
        if fi == i: d.rectangle([x - 2, y - 2, x + cw + 1, y + ch + 1], outline=(235, 50, 50), width=3)
        d.text((x + 2, y + ch + 2), f'{fi / fps:.3f}s {fi - i:+d}' + ('  空' if k < len(empty) and empty[k] else ''), fill=(255, 90, 90) if k < len(empty) and empty[k] else (255, 220, 0), font=f)
    p = ROOT / 'frames' / '_view' / f'blank_{i / fps:.2f}s.jpg'; p.parent.mkdir(parents=True, exist_ok=True); sh.save(p, quality=84)
    return str(p), [round(a / fps, 3), round(b / fps, 3)], b - a + 1


def blank_advice(sid, prev):
    """拍点空画面的改法：镜头起点和镜头里的半拍不一样"""
    if sid:
        return (f'切点那一帧是空的：让下一个镜头 {sid} 提前入场（SHOT.{sid} 写 pre，或把入场 enter 的起点挪到切点之前），'
                f'或让上一个镜头 {prev or "（前一个）"} 晚点退场（post），切点那一帧要有画面')
    return '这半拍画面是空的：上一组内容退完、下一组还没进来。让下一组的入场提前（enter 起点挪到这一拍之前），或让上一组留到下一组进来'


def loudness(path):
    r = subprocess.run([FF, '-i', path, '-map', '0:a', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    try:
        return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1]), float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r)[-1])
    except Exception:
        return None, None


def novelty(path, w, h):
    """每 0.1 秒一个值：此刻与 0.5 秒前的画面差（64 像素宽灰度、3×3 模糊）。低于 LOW 表示这半秒里观众看不到新东西。"""
    from scipy.ndimage import uniform_filter
    sw = 64; sh = max(2, round(sw * h / w / 2) * 2)
    r = subprocess.run([FF, '-loglevel', 'error', '-i', path, '-vf', f'fps={NFPS}:round=up,scale={sw}:{sh}:flags=area,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    n = sw * sh
    f = [uniform_filter(np.frombuffer(r[i:i + n], np.uint8).reshape(sh, sw).astype(np.float32), 3) for i in range(0, len(r) - n + 1, n)]
    k = int(LAG * NFPS)
    return np.array([np.abs(f[i] - f[i - k]).mean() for i in range(k, len(f))])


def low_runs(nov):
    """低变化的连续段 [(起点秒, 长度秒)]，长度包含 0.5 秒的比较间隔；最后一段如果延续到片尾，单独作为结尾停留。"""
    runs, s0 = [], None
    for i, v in enumerate(list(nov < LOW) + [False]):
        if v and s0 is None: s0 = i
        if not v and s0 is not None: runs.append((s0, i)); s0 = None
    sec = lambda r: (round(r[0] / NFPS, 1), round((r[1] - r[0]) / NFPS + LAG, 1))
    tail = runs.pop() if runs and runs[-1][1] >= len(nov) - 1 else None
    return [sec(r) for r in runs], (sec(tail) if tail else None)


def wash_series(path, w, h, size=128):
    """逐帧流式读取，每帧留：背景色的亮度（灰度直方图的众数）、背景的色彩饱和度（众数附近像素的 max-min）、灰度直方图（64 档，占比）。"""
    sw, sh = (size, max(2, round(size * h / w / 2) * 2)) if w >= h else (max(2, round(size * w / h / 2) * 2), size)
    p = subprocess.Popen([FF, '-loglevel', 'error', '-i', path, '-vf', f'scale={sw}:{sh}:flags=area,format=rgb24', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    n = sw * sh * 3; M, C, Hs = [], [], []
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        a = np.frombuffer(b, np.uint8).reshape(sh, sw, 3).astype(np.float32); g = a.mean(2)
        raw = np.bincount((g.reshape(-1) // 4).astype(int), minlength=64).astype(float)
        hist = np.convolve(raw, [1, 2, 1], 'same')
        m = hist.argmax() * 4 + 2; sel = np.abs(g - m) <= 10
        M.append(m); C.append(float((a[sel].max(1) - a[sel].min(1)).mean()) if sel.any() else 0.0); Hs.append(raw / raw.sum())
    p.wait(); return np.array(M), np.array(C), np.array(Hs)


def near(Hf, m, tol=10):
    """这一帧里灰度在 m ± tol 以内的像素占比（Hf 是 wash_series 的 64 档直方图）"""
    return float(Hf[max(0, int(m - tol) // 4):min(64, int(m + tol) // 4 + 1)].sum())


def find_washes(M, C, fps, Hs=None, lift=20, peak=30, min_frames=2, chroma=35, ret=12, keep=0.5):
    """整帧被闪光刷灰：这一帧的背景亮度比 0.2 秒前、0.4 秒后都高出 lift 以上（后两者相差不大，即闪完回到原样），背景是中性灰（饱和度低），
    原来的背景亮度在这一帧里几乎没有了（整帧被抬亮），连续 ≥ min_frames 帧，且最高抬升 ≥ peak。返回 [(起点秒, 帧数, 最高抬升)]。
    三种情况不报：①闪完没有回到原样的是换了场景（例如暗底切到浅底）；②背景铺成有明显颜色的纯色面（品牌色擦过去）；
    ③原来背景亮度的像素在这一帧还剩 keep 以上：画面里两块大色面各占一半左右（推近后物件和纸面），众数在两者之间来回跳，背景没有被刷。
    阈值用 21 支片校准（见 references/review.md）。背景本身很亮的片子，加亮的空间小，这项检查测不出来。"""
    k, m, n = max(1, round(0.2 * fps)), max(2, round(0.4 * fps)), len(M)
    hit = np.zeros(n, bool)
    for i in range(k, n - m):
        mb, ma = M[i - k], M[i + m]
        hit[i] = abs(ma - mb) <= ret and M[i] - max(mb, ma) >= lift and C[i] <= chroma
        if hit[i] and Hs is not None: hit[i] = near(Hs[i], mb) < keep * near(Hs[i - k], mb)
    out, i = [], 0
    while i < n:
        if not hit[i]: i += 1; continue
        j = i
        while j + 1 < n and hit[j + 1]: j += 1
        up = float(M[i:j + 1].max() - M[i - k])
        if j - i + 1 >= min_frames and up >= peak: out.append((round(i / fps, 2), j - i + 1, int(up)))
        i = j + 1
    return out


def main():
    info = probe(V); fps = info['fps']
    res = dict(info, genre=GENRE, video=V)
    nov = novelty(V, info['width'], info['height'])
    runs, tail = low_runs(nov)
    res['novelty_median'] = round(float(np.median(nov)), 2)
    res['low_share'] = round(float((nov < LOW).mean()), 2)
    lg = max(runs, key=lambda r: r[1]) if runs else None
    res['longest_low'] = lg[1] if lg else 0.0
    res['longest_low_at'] = lg[0] if lg else None
    res['end_hold'] = tail[1] if tail else 0.0
    res['low_segments'] = [r for r in runs if r[1] >= 1.5]
    g = grey_frames(V, info['width'], info['height'])
    d = np.array([np.abs(g[i] - g[i - 1]).mean() for i in range(1, len(g))])
    res['motion_mean'] = round(float(d.mean()), 3)
    res['diff_series'] = [round(float(x), 2) for x in d]          # 相邻帧灰度差（逐帧），体检的对齐图画成画面变化量曲线
    # 切点：差值远高于前后邻域
    cuts = []
    for i in range(2, len(d) - 2):
        nb = np.median(np.r_[d[max(0, i - 4):i], d[i + 1:i + 5]])
        if d[i] > max(6.0, 4 * nb) and d[i] == d[max(0, i - 2):i + 3].max(): cuts.append((i + 1) / fps)
    res['cuts'] = [round(c, 3) for c in cuts]
    res['cuts_per_sec'] = round(len(cuts) / max(1e-6, info['duration']), 2)
    # 单帧跳变：突变后马上回到原状态（闪一帧），通常是 bug
    pops = []
    for i in range(1, len(g) - 1):
        a, b_, c = g[i - 1], g[i], g[i + 1]
        if np.abs(b_ - a).mean() > 6 and np.abs(b_ - c).mean() > 6 and np.abs(c - a).mean() < 1.5: pops.append(round(i / fps, 3))
    res['pops'] = len(pops); res['pop_times'] = pops[:20]
    blank = []
    for f in (ROOT / 'frames' / '_view').glob('blank_*.jpg'): f.unlink()          # 上一次体检的逐帧条
    order = sorted(TL['scenes'].values(), key=lambda s: s['t0']) if TL else []
    for i, sid in beat_points(fps):
        if i >= len(g) or edge_share(g[i]) >= BLANK: continue
        prev = next((order[k - 1]['id'] for k in range(1, len(order)) if order[k]['id'] == sid), None) if sid else None
        img, run, nb = blank_strip(V, info, g, i, sid)
        blank.append(dict(t=round(i / fps, 3), frame=i, cut=sid, prev=prev, run=run, n_blank=nb, strip=img, advice=blank_advice(sid, prev)))
    res['blank_beats'] = len(blank); res['blank_beat_times'] = [b['t'] for b in blank][:20]; res['blank_beat_list'] = blank[:20]
    Mb, Cb, Hb = wash_series(V, info['width'], info['height'])
    ws = find_washes(Mb, Cb, fps, Hb)
    res['washes'] = len(ws); res['wash_list'] = ws[:20]
    if TL and TL.get('bpm') and cuts:
        beat = TL['beat']; off = TL.get('offset', 0); tol = 1.5 / fps
        grid = beat / 2
        hit = [abs((c - off) / grid - round((c - off) / grid)) * grid <= tol for c in cuts]
        res['cuts_on_halfbeat'] = round(float(np.mean(hit)), 2)
        res['cuts_on_halfbeat_chance'] = round(min(1.0, 2 * tol / grid), 2)
    ims, (tw, th) = rgb_frames(V, info['width'], info['height'], 0.5)
    fills = [fill_ratio(im) for im in ims]
    res['fill_mean'] = round(float(np.mean(fills)), 3) if fills else None
    res['fill_low_times'] = [round(i * 0.5, 1) for i, f in enumerate(fills) if f < 0.02][:20]
    if info['audio']:
        res['loudness'], res['true_peak'] = loudness(V)
    # 总览图
    cols = 8 if info['width'] >= info['height'] else 10
    for gi in range(0, len(ims), cols * 6):
        chunk = ims[gi:gi + cols * 6]; rows = (len(chunk) + cols - 1) // cols
        sh = Image.new('RGB', (cols * (tw + 4) + 4, rows * (th + 4) + 4), (40, 40, 40)); dr = ImageDraw.Draw(sh)
        for j, im in enumerate(chunk):
            x, y = 4 + (j % cols) * (tw + 4), 4 + (j // cols) * (th + 4); t = (gi + j) * 0.5
            sh.paste(Image.fromarray(im), (x, y))
            lab = f'{t:.1f}s' + (f' b{(t - TL.get("offset", 0)) / TL["beat"]:.0f}' if TL and TL.get('bpm') else '')
            dr.rectangle([x, y, x + 7 * len(lab) + 6, y + 14], fill=(0, 0, 0)); dr.text((x + 3, y + 1), lab, fill=(255, 220, 0))
        p = ROOT / 'frames' / '_view' / f'review_{gi // (cols * 6):02d}.jpg'; p.parent.mkdir(parents=True, exist_ok=True); sh.save(p, quality=84)
        print('总览', p)
    (ROOT / 'out').mkdir(exist_ok=True)
    json.dump(res, open(ROOT / 'out' / 'review.json', 'w'), ensure_ascii=False, indent=1)

    names = {'novelty_median': '新内容（中位数）', 'low_share': '低变化时间占比', 'longest_low': '片中最长低变化段（秒）', 'end_hold': '结尾停留（秒）',
             'fill_mean': '画面占用率', 'blank_beats': '拍点空画面（个）', 'washes': '整帧被闪光刷灰（处）', 'loudness': '响度 LUFS', 'true_peak': '真峰值 dBFS', 'pops': '单帧跳变（个）'}
    print(f"\n{info['width']}×{info['height']} · {fps:g} fps · {info['duration']:.2f} 秒 · {'有声' if info['audio'] else '无声'} · 质量线：{GENRE}")
    bad = 0
    for k, (lo, hi, guard) in BAR.items():
        v = res.get(k)
        if v is None: continue
        ok = (lo is None or v >= lo) and (hi is None or v <= hi)
        rng_ = f"≥ {lo}" if hi is None else f"≤ {hi}" if lo is None else f"{lo} ~ {hi}"
        mark = '✅' if ok else ('ℹ️' if not guard else '❌' if k in ('pops', 'true_peak', 'blank_beats') else '⚠️')
        bad += (not ok) and guard
        extra = f"（从 {res['longest_low_at']} 秒开始）" if k == 'longest_low' and not ok else ''
        print(f'  {mark} {names[k]:14s} {v:>8}   {"目标" if guard else "参考"} {rng_}{extra}')
    if res['low_segments']: print(f"  · 1.5 秒以上的低变化段（起点秒, 长度秒）：{res['low_segments']}")
    print(f"  · 切点 {len(cuts)} 个（每秒 {res['cuts_per_sec']}）" + (f"，落在半拍上的比例 {res['cuts_on_halfbeat']}（随机水平 {res['cuts_on_halfbeat_chance']}）" if 'cuts_on_halfbeat' in res else ''))
    if res['fill_low_times']: print(f"  · 画面几乎是空的时刻：{res['fill_low_times']}")
    if pops: print(f'  · 单帧跳变时刻：{pops[:10]}')
    if res['blank_beat_times']:
        print('  · 拍点空画面（镜头起点或半拍上那一帧是空的，常见原因：入场从这一拍才开始，弹簧在这一帧值为 0）：')
        for b_ in blank:
            print(f"    {b_['t']:.2f}s" + (f"（{b_['prev']} > {b_['cut']} 的切点）" if b_['cut'] else '（半拍）') +
                  f"：空帧 {b_['run'][0]:.2f}–{b_['run'][1]:.2f}s 共 {b_['n_blank']} 帧。{b_['advice']}。逐帧条 {b_['strip']}")
        if res['blank_beat_times'][0] < 0.01:
            print("  · 第 0 帧是空的：宣传片第一帧必须有内容（缩略图和自动播放的首帧就是它）。先看 project.json 的 post.fadeIn，有的话删掉或设 0；再看第一个镜头的入场是不是从 0 秒才开始")
    if res['wash_list']:
        print("  · 整帧被闪光刷灰（时刻秒, 持续帧数, 背景最高抬升）：" + str(res['wash_list'])
              + "。这几帧里背景被整体提亮。用 stills.py 看这几帧：主体还清楚、只有 1–2 帧的有意闪白可以保留；"
              + "主体被洗淡、灰底持续好几帧，就改用 FLASH 的默认 light 模式（只提亮内容），或缩短衰减、只给主体加光晕")
    print(f"\n{'全部达标' if not bad else f'{bad} 项没达标'}。数字只能发现问题，不能证明好看：再对照总览图和 references/review.md 的检查清单看一遍。")


if __name__ == '__main__':
    main()
