"""参考视频拆解：把一支参考片拆成切点表、每段的首/中/尾帧、0.1 秒间隔的节奏总览，并估计画幅、帧率、BPM。
  python3 tools/refsheet.py <视频> [名字]  [--start 秒] [--end 秒] [--thresh 8] [--ev-thresh 4]
输出（名字默认取文件名）：
  frames/_view/ref_<名字>_cuts.jpg          每段一行：首 / 中 / 尾帧，标出起止时刻和时长（段多时分页 _cuts_2…）
  frames/_view/ref_<名字>_t1.jpg …          每 0.1 秒一帧的节奏总览，按时间排，红框 = 这 0.1 秒内有硬切，橙框 = 有变化点（分页）
  assets/ref.json                           { 名字: {画幅, 帧率, 时长, 切点, 分段, 变化点, BPM, 节奏统计} }，多支参考片并存
终端打印切点表和变化点。只读 frames/_view/ 里的 JPEG。
两类事件，缩小到 160 像素宽后逐帧算与上一帧的平均像素差：
  硬切（整屏换镜头）：单帧尖峰，差值 ≥ --thresh（0 到 255），且 ≥ 前后几帧最大差值的 2.2 倍。分段按它切。
  变化点（同一版面里换词、换数字、元素进场）：2 到 8 帧的差值脉冲，≥ --ev-thresh。快剪字幕片的节奏主要在这里，不在硬切上。
  持续 8 帧以上的运动（滚动、变形、推拉）单独列为「持续运动」。
  形态变化点（连续变形的片子：按钮变播放器变开关）：帧差平滑后（0.2 秒）的峰值，没有硬切也能看出每个形态在哪一刻换。
渐变转场、闪白检不出来：对照 _t 总览补。
"""
import sys, os, re, json, argparse, subprocess, tempfile, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, ffmpeg

VIEW = ROOT / 'frames' / '_view'
HERE = Path(__file__).resolve().parent


def probe(src):
    """宽高、帧率、时长、有无音轨（从 ffmpeg -i 的输出里读，没有 ffprobe）。"""
    t = subprocess.run([ffmpeg(), '-hide_banner', '-i', str(src)], capture_output=True, text=True).stderr
    m = re.search(r'Video:.*?,\s*(\d{2,5})x(\d{2,5})', t); fps = re.search(r'([\d.]+) fps', t); d = re.search(r'Duration:\s*(\d+):(\d+):([\d.]+)', t)
    if not (m and d): sys.exit('读不出视频信息：' + t[-300:])
    rot = re.search(r'rotate\s*:\s*(-?\d+)', t); w, h = int(m.group(1)), int(m.group(2))
    if rot and abs(int(rot.group(1))) in (90, 270): w, h = h, w
    return {'w': w, 'h': h, 'fps': float(fps.group(1)) if fps else 30.0, 'dur': int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)), 'audio': 'Audio:' in t}


def frame_diffs(src, fps, t0, t1):
    """缩小后逐帧读出，返回 每帧与上一帧的平均像素差 [N]（第 0 帧为 0）。"""
    W = 160; info = probe(src); H = max(2, round(W * info['h'] / info['w'] / 2) * 2)
    cmd = [ffmpeg(), '-v', 'error', '-ss', str(t0), '-t', str(t1 - t0), '-i', str(src), '-vf', f'fps={fps},scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE); n = W * H * 3; prev = None; d = []
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        f = np.frombuffer(b, np.uint8).astype(np.int16)
        d.append(0.0 if prev is None else float(np.abs(f - prev).mean())); prev = f
    p.wait()
    return np.array(d)


def find_events(d, ev_thresh, cuts):
    """变化点：连续超过阈值的帧成一簇（中间最多断 1 帧）。8 帧以内的簇是变化点（取起点），更长的是持续运动。硬切所在的簇不算。返回 (变化点, 持续运动)。"""
    ev, mo, i, n = [], [], 1, len(d)
    while i < n:
        if d[i] < ev_thresh: i += 1; continue
        j = i
        while j + 1 < n and (d[j + 1] >= ev_thresh or (j + 2 < n and d[j + 2] >= ev_thresh)): j += 1
        if not any(i - 1 <= c <= j + 1 for c in cuts):
            (ev if j - i + 1 <= 8 else mo).append((i, j, float(d[i:j + 1].max())))
        i = j + 1
    return ev, mo


def find_activity(d, fps):
    """帧差平滑（0.2 秒）后的峰值：连续变形的片子里每个形态变化的时刻。返回 [(时刻, 强度)]。"""
    from scipy.signal import find_peaks
    from scipy.ndimage import uniform_filter1d
    sm = uniform_filter1d(d, max(1, int(0.2 * fps))); base = float(np.median(sm))
    pk, _ = find_peaks(sm, height=max(0.8, 1.5 * base), prominence=max(0.5, 0.3 * float(np.percentile(sm, 90))), distance=max(1, int(0.4 * fps)))
    return [(float(p / fps), float(sm[p])) for p in pk]


def find_cuts(d, thresh):
    """硬切：差值 ≥ 阈值，且 ≥ 前后 4 帧里最大差值的 2.2 倍（排除快速运动和闪烁），相邻 3 帧内只留最大的。"""
    cuts = []
    for i in range(1, len(d)):
        if d[i] < thresh: continue
        nb = np.concatenate([d[max(1, i - 4):i], d[i + 1:i + 5]])
        if len(nb) and d[i] < 2.2 * nb.max(): continue
        if cuts and i - cuts[-1] <= 3:
            if d[i] > d[cuts[-1]]: cuts[-1] = i
            continue
        cuts.append(i)
    return cuts


def estimate_bpm(src, t0, t1):
    """复用 audio/beat_detect.py（它是脚本，用子进程调用）。没有音轨或太短返回 None。"""
    bd = HERE.parent / 'audio' / 'beat_detect.py'
    if not bd.exists(): return None
    tmp = Path(tempfile.mkdtemp()) / 'a.wav'
    subprocess.run([ffmpeg(), '-v', 'error', '-y', '-ss', str(t0), '-t', str(t1 - t0), '-i', str(src), '-vn', '-ac', '1', '-ar', '22050', str(tmp)], capture_output=True)
    if not tmp.exists(): return None
    r = subprocess.run([sys.executable, str(bd), str(tmp), '--out', str(tmp.with_suffix('.jpg'))], capture_output=True, text=True)
    shutil.rmtree(tmp.parent, ignore_errors=True)
    m = re.search(r'估计 BPM\s*([\d.]+)\s+第一拍\s*([\d.]+)s\s+置信\s*(\S+)', r.stdout)
    return {'bpm': float(m.group(1)), 'first_beat': float(m.group(2)), 'confidence': m.group(3).strip('，,')} if m else None


def font(n=15):
    for fp in ('/System/Library/Fonts/STHeiti Light.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc', '/System/Library/Fonts/PingFang.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'):
        try: return ImageFont.truetype(fp, n)
        except Exception: pass
    return ImageFont.load_default()


def grab(src, ts, w):
    """取一批时刻的帧（缩到宽 w）。"""
    out = []
    for t in ts:
        r = subprocess.run([ffmpeg(), '-v', 'error', '-ss', f'{t:.3f}', '-i', str(src), '-frames:v', '1', '-vf', f'scale={w}:-2', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-q:v', '3', '-'], capture_output=True).stdout
        out.append(Image.open(__import__('io').BytesIO(r)).convert('RGB') if r else None)
    return out


def sheet_cuts(src, segs, name, info):
    """每段一行：首/中/尾帧。竖版一行 3 帧并排，每页 6 段；横版每页 8 段。"""
    portrait = info['h'] > info['w']; fw = 150 if portrait else 300; per = 6 if portrait else 8
    ft = font(15); paths = []
    for pi in range(0, len(segs), per):
        pg = segs[pi:pi + per]; fh = round(fw * info['h'] / info['w']); LW = 130
        im = Image.new('RGB', (LW + 3 * (fw + 6), len(pg) * (fh + 6) + 6), (28, 28, 30)); d = ImageDraw.Draw(im)
        for r, s in enumerate(pg):
            y = 6 + r * (fh + 6)
            d.text((8, y + 4), f'#{s["i"]}', fill=(255, 220, 0), font=font(20)); d.text((8, y + 32), f'{s["t0"]:.2f}–{s["t1"]:.2f}s', fill=(230, 230, 230), font=ft)
            d.text((8, y + 54), f'{s["dur"]:.2f}s', fill=(255, 220, 0), font=ft); d.text((8, y + 76), f'动态 {s["motion"]:.1f}', fill=(150, 150, 150), font=ft)
            eps = 0.5 / info['fps']
            for c, t in enumerate((s['t0'] + eps, (s['t0'] + s['t1']) / 2, s['t1'] - 1.5 * eps)):
                f = grab(src, [max(0, t)], fw)[0]
                if f: im.paste(f, (LW + c * (fw + 6), y))
        p = VIEW / (f'ref_{name}_cuts.jpg' if pi == 0 else f'ref_{name}_cuts_{pi // per + 1}.jpg'); im.save(p, quality=85); paths.append(p)
    return paths


def sheet_beat(src, t0, t1, cuts_t, ev_t, name, info, step=0.1):
    """每 0.1 秒一帧，按时间排；红框 = 硬切，橙框 = 变化点。"""
    portrait = info['h'] > info['w']; cols = 10 if portrait else 6; tw = 144 if portrait else 250
    th = round(tw * info['h'] / info['w']); rows_pp = 3 if portrait else 5; per = cols * rows_pp
    ts = list(np.arange(t0, t1 - 1e-6, step)); ft = font(13); paths = []
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([ffmpeg(), '-v', 'error', '-ss', str(t0), '-t', str(t1 - t0), '-i', str(src), '-vf', f'fps={1 / step:g},scale={tw}:-2', '-q:v', '4', str(tmp / '%05d.jpg')], capture_output=True)
    frames = sorted(tmp.glob('*.jpg'))
    for pi in range(0, len(ts), per):
        chunk = ts[pi:pi + per]; rows = (len(chunk) + cols - 1) // cols
        im = Image.new('RGB', (cols * (tw + 4) + 4, rows * (th + 20) + 4), (28, 28, 30)); d = ImageDraw.Draw(im)
        for k, t in enumerate(chunk):
            x, y = 4 + (k % cols) * (tw + 4), 4 + (k // cols) * (th + 20); j = pi + k
            if j < len(frames): im.paste(Image.open(frames[j]).convert('RGB').resize((tw, th)), (x, y))
            cut = any(t - 1e-6 <= c < t + step - 1e-6 for c in cuts_t)
            ev = any(t - 1e-6 <= c < t + step - 1e-6 for c in ev_t)
            if cut: d.rectangle([x - 2, y - 2, x + tw + 1, y + th + 1], outline=(255, 60, 60), width=3)
            elif ev: d.rectangle([x - 2, y - 2, x + tw + 1, y + th + 1], outline=(255, 170, 40), width=2)
            d.text((x + 2, y + th + 2), f'{t:.1f}' + (' 切' if cut else ' 变' if ev else ''), fill=(255, 120, 120) if cut else (255, 190, 90) if ev else (200, 200, 200), font=ft)
        p = VIEW / f'ref_{name}_t{pi // per + 1}.jpg'; im.save(p, quality=82); paths.append(p)
    shutil.rmtree(tmp, ignore_errors=True)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video'); ap.add_argument('name', nargs='?'); ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float)
    ap.add_argument('--thresh', type=float, default=8, help='硬切的最小帧差（0–255 的平均像素差）。白底版面帧差小，漏检就调低；误检就调高')
    ap.add_argument('--ev-thresh', type=float, default=4, help='变化点的最小帧差')
    a = ap.parse_args(); src = Path(a.video)
    if not src.exists(): sys.exit(f'找不到视频：{src}')
    name = a.name or re.sub(r'[^A-Za-z0-9_]+', '_', src.stem)[:24]; info = probe(src)
    t0, t1 = a.start, min(a.end or info['dur'], info['dur']); VIEW.mkdir(parents=True, exist_ok=True)
    fps = min(info['fps'], 60); d = frame_diffs(src, fps, t0, t1); idx = find_cuts(d, a.thresh)
    cuts_t = [round(t0 + i / fps, 3) for i in idx]; bounds = [t0] + cuts_t + [t1]
    segs = []
    for k in range(len(bounds) - 1):
        i0, i1 = int(round((bounds[k] - t0) * fps)), int(round((bounds[k + 1] - t0) * fps))
        mo = d[i0 + 1:i1] if i1 - i0 > 1 else np.array([0.0])
        segs.append({'i': k + 1, 't0': round(bounds[k], 3), 't1': round(bounds[k + 1], 3), 'dur': round(bounds[k + 1] - bounds[k], 3), 'motion': round(float(mo.mean()), 2)})
    ev, mo = find_events(d, a.ev_thresh, idx); act = [(round(t0 + t, 2), round(v, 1)) for t, v in find_activity(d, fps)]
    ev_t = [round(t0 + e[0] / fps, 3) for e in ev]; mo_t = [[round(t0 + m[0] / fps, 2), round(t0 + (m[1] + 1) / fps, 2)] for m in mo]
    bp = estimate_bpm(src, t0, t1) if info['audio'] and t1 - t0 >= 4 else None
    durs = np.array([s['dur'] for s in segs]); med = float(np.median(durs))
    rhythm = {'segments': len(segs), 'cuts': len(cuts_t), 'cuts_per_sec': round(len(cuts_t) / (t1 - t0), 2), 'median_seg': round(med, 3), 'shortest': round(float(durs.min()), 3), 'longest': round(float(durs.max()), 3)}
    allp = sorted(ev_t + cuts_t); gaps = np.diff(allp) if len(allp) > 1 else np.array([])
    if len(gaps): rhythm.update({'change_points': len(allp), 'change_interval_median': round(float(np.median(gaps)), 3)})
    if bp:
        rhythm['median_seg_in_beats'] = round(med * bp['bpm'] / 60, 2)
        if len(gaps): rhythm['change_interval_in_beats'] = round(float(np.median(gaps)) * bp['bpm'] / 60, 2)
    print(f'{src.name}：{info["w"]}×{info["h"]}（{"竖版" if info["h"] > info["w"] else "横版" if info["w"] > info["h"] else "方形"}）{info["fps"]:g} fps  {t0:g}–{t1:g}s（{t1 - t0:.2f}s）' + ('  无音轨' if not info['audio'] else ''))
    print(f'硬切 {len(cuts_t)} 处，分 {len(segs)} 段；每秒 {rhythm["cuts_per_sec"]} 切，段长中位 {med:.2f}s（最短 {durs.min():.2f}s，最长 {durs.max():.2f}s）')
    if bp: print(f'BPM ≈ {bp["bpm"]:g}（置信 {bp["confidence"]}），第一拍 {bp["first_beat"]:.3f}s；段长中位约 {rhythm["median_seg_in_beats"]} 拍（注意：切点是否落在拍上要看 _t 总览和声音）')
    elif info['audio']: print('音轨太短，没估 BPM')
    if len(gaps): print(f'变化点（含硬切）{len(allp)} 个，间隔中位 {np.median(gaps):.2f}s' + (f'，约每 {rhythm["change_interval_in_beats"]} 拍一次' if bp else '') + '：' + ' '.join(f'{t:.2f}' for t in allp[:40]) + (' …' if len(allp) > 40 else ''))
    if act: print('形态变化点（帧差平滑后的峰值，括号内是强度）：' + ' '.join(f'{t:.2f}({v:g})' for t, v in act[:30]))
    if mo_t: print('持续运动（滚动、变形、推拉）：' + '、'.join(f'{x}–{y}s' for x, y in mo_t[:10]))
    print('\n段   起止(s)          时长    动态')
    for s in segs: print(f'#{s["i"]:<3d} {s["t0"]:6.2f}–{s["t1"]:6.2f}   {s["dur"]:5.2f}s  {s["motion"]:5.1f}' + ('  ← 帧差低：静止或慢动作' if s['motion'] < 1.5 else '  ← 帧差高：段内大幅运动/可能漏检切点' if s['motion'] > 25 else ''))
    p1 = sheet_cuts(src, segs, name, info); p2 = sheet_beat(src, t0, t1, cuts_t, ev_t, name, info)
    out = ROOT / 'assets' / 'ref.json'; out.parent.mkdir(exist_ok=True)
    data = json.load(open(out, encoding='utf-8')) if out.exists() else {}
    data[name] = {'source': str(src), 'size': [info['w'], info['h']], 'fps': info['fps'], 'range': [t0, t1], 'bpm': bp, 'rhythm': rhythm, 'cuts': cuts_t, 'segments': segs, 'change_points': ev_t, 'activity_peaks': act, 'continuous_motion': mo_t,
                  'sheets': {'cuts': [str(p.relative_to(ROOT)) for p in p1], 'beat': [str(p.relative_to(ROOT)) for p in p2]}}
    json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n总览：' + '  '.join(str(p.relative_to(ROOT)) for p in p1 + p2) + '\n数据：assets/ref.json')
    print('只读这些缩小的 JPEG。借手法，不照抄设计：看每段多长、字怎么出现、转场怎么做、节奏密度，再用自己的内容和风格做。')


if __name__ == '__main__':
    main()
