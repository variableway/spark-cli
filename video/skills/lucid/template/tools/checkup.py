"""体检：python3 tools/checkup.py [--format 名字] [--video 成片路径] [--track 登记.json] [--layout 版面结果.json] [--no-review]
render.py 渲完会自动调用它（草稿档也跑），终端只打印摘要；改了镜头只想重查时可以单独运行。
一条命令跑完：版面审计（layout.py）、开场、转场、抖动（读渲染时记下的镜头矩阵，不看像素）、讲解片的短句对齐、同框文字冲突，
有成片时再跑成片体检（review.py）、静止段和时长（motioncheck.py）、空帧；体检的是正式档时，再和草稿档逐帧比对找重影（ghostcheck.py）。
--video 不给时按顺序找 out/ 下的正式档、草稿档。--track 是 render.py 渲这支成片时每帧记下的登记（镜头矩阵、画面事件、新出现的字），
不给时找 out/segments/full_<画幅>_<档>_track.json；也没有就在页面上逐帧补一遍（慢）。--layout 直接用 render.py 渲染前刚跑过的版面结果。

检查分两级。体检只拦观众看得见的硬伤；版式、节奏、镜头运动怎么设计由片子自己定，相关的量只作为可选提示。
  硬伤（❌ 要改，⚠️ 打开总览图对应编号看一眼再决定；进终端摘要和问题条数）：
    文字出框、文字互相压住（含换句时短暂叠在一起、同框两段字推迟不了而叠在一起）、字太小（低于可读下限）、标注没落到目标、线穿过文字、
    画面内容进了字幕带、占位字、开场空画面、空帧、拍点空画面、单帧跳变、正式档重影、「稳」镜头里的快抖、时长对目标。
    字幕和配音不一致由 timeline.py 和 tts.py 的转写核对拦；合同违规（只依赖 t、不用 Math.random、不丢全局矩阵、EV 写在顶层）由 render.py 渲染前的 lint.py 拦。
  可选提示（ℹ️；只写进报告「可选提示」一节，不算问题）：
    主体偏小、留白多，画面停住，这句话画面没有新事件，镜头重叠段 / 通用 fade 转场，整帧被刷灰，同框换句已自动推迟，
    文字块放不下（照最小字号画了），线头悬空，过程标注词，直接用 fillText 画的字，「可以震」镜头偏多，可以震的镜头里的抖动、单次震动太长。
终端摘要：「硬伤 N 条（❌ a、⚠️ b）；可选提示 M 条见报告」，下面只列硬伤。

输出在 frames/_view/checkup/（多画幅时是 checkup_<画幅>/）：
  报告.md      问题清单（硬伤，编号，❌ 在前，按时间排）→ 可选提示 → 各项检查 → 按镜头（内容覆盖、最大字高、问题编号）→ 装饰字豁免 → 图
               每条一行：编号. ❌ S05 · 12.3s · web/shots_05.js:27 · 「几十年内」 · 文字出框（右侧超出画面 18px）
  总览.jpg     一张图看全片：每个镜头 2–3 帧，有硬伤的帧画框并标编号，编号和问题清单对应；橙色边框是「主体偏小」提示。宽不超过 1600 px
  对齐.jpg     讲解片：每个镜头一条，灰条是配音短句，竖线是 act() 登记的画面事件，小三角是新出现的字，曲线是画面变化量（草稿成片的相邻帧差）。
               标红的短句是「这句话画面没有新事件」
  trail_<镜头>.jpg  洋葱皮（8 帧叠在一起），报告里只在要看运动的条目（抖动、震动）引用
  空帧.jpg     报了空帧时：每段一格（那一段中间的一帧）
  ghost_N.jpg  报了正式档重影时：峰值那一帧，左正式档、右草稿档
  checkup.json 全部结果，render.py 读它打印摘要
全部通过只说明没有基础错误；片子好不好，要看成片定。

几项要说明判据的检查：
  空帧（⚠️，成片）  取全片每个像素的中位数作背景板（静止的纹理底、网格也算背景）；偏离背景板的像素少于 1.5%，而且偏离这一帧主背景色
                    （四边像素的中位色）的像素少于 4%，持续 0.3 秒以上（片头片尾各 0.5 秒不查）。多半是上一组内容退完、下一组还没进来。
                    留白是设计（一句话前的停顿、落版的呼吸）时，在交付说明里写一句即可。镜头一直在动的片子背景板会糊，只会少报。
                    整屏色块（去掉四边 8% 后几乎没有边缘，不是黑场）持续 0.3 秒以上也报：满屏一块颜色或渐变，多半是转场色块停住了。
  文字互相压住（短暂，⚠️）  渲染时逐帧查同一种字（字体字号相同）的两段不同文字（可见度都 > 0.3）外框明显相交，持续不到 0.5 秒的（换句时前一段没退完、后一段已进来）。
                    版面审计的取样点碰不到这一两帧。持续更久的由版面审计判断（它会算卡片的遮挡）。
  拍点空画面（❌，成片）  镜头起点、节拍片的每个半拍那一帧（先换算成帧号再去重，同一帧只报一次）画面上几乎没有边缘。每条带
                    blank_<秒>s.jpg：拍点前 0.2 秒到后 0.3 秒逐帧，拍点那一帧红框、空的帧标「空」；说明写切点两侧的镜头和改法
                    （下一个镜头提前入场 pre / enter，或上一个镜头晚点退场 post）。
  正式档重影（❌，正式档）  和草稿档逐帧比，正式档里出现草稿档同一位置没有的清晰边缘、连续 2 帧以上、画面在动。判据见 ghostcheck.py 文件头。
                    草稿档早于当前代码时跳过（提示先重渲草稿档）。
  主体偏小、留白多（ℹ️）  一个镜头的内容覆盖和最大字高（取样点中位数）都低于 layout.py 的 SUBJECT_MIN：讲解片 覆盖 < 30% 且 字高 < 短边 4.0%；
                    宣传片 覆盖 < 35% 且 字高 < 短边 5.0%。同时给出能照着改的量（等比放大到约几倍可占满安全区、哪一侧空）。留白是设计时不用管。
  这句话画面没有新事件（ℹ️，讲解片）  短句开头前 0.3 秒到后 0.6 秒内，既没有 act() 登记的事件开始，也没有新的字出现，成片里画面也没有明显变化。按镜头合并。
"""
import sys, io, json, re, math, time, subprocess, contextlib, threading, shutil
from pathlib import Path
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from common import ROOT, serve, open_page, timeline, pop_format, formats, project, uses_gpu, gpu_slot, out_name, snap, font, frame_at, subtitles, TRACK_JS, FRAME_JS, TRACK_FLUSH_JS

ARGV = sys.argv[1:]
FMT = pop_format(ARGV)[0]
def _opt(n):
    if n in ARGV: i = ARGV.index(n); v = ARGV[i + 1]; del ARGV[i:i + 2]; return v
    return None
VIDEO, LAYOUT, TRACK = _opt('--video'), _opt('--layout'), _opt('--track')
NO_REVIEW = '--no-review' in ARGV
_argv = sys.argv; sys.argv = ['layout.py']
from layout import content_stats, SUBJECT_MIN, fmt_line, enlarge_hint, summary_line   # 同一套主体口径和摘要口径，和 layout.py 一致
sys.argv = _argv
CFG = project(); TL = timeline(); FW, FH = formats()[FMT]
GENRE = CFG.get('genre') or ('explainer' if TL.get('mode') == 'voice' else 'promo')
MULTI = len(formats()) > 1
OUT = ROOT / 'frames' / '_view' / ('checkup' + (f'_{FMT}' if MULTI else '')); OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob('*'): f.unlink()
ORDER = sorted(TL['scenes'].values(), key=lambda s: s['t0'])
TOTAL = TL['total']
T_START = time.time(); TIMING = {}
ALIGN_PRE, ALIGN_POST = 0.3, 0.6 
MOTION_EVENT_K, MOTION_EVENT_MIN = 2.0, 0.6                       # 画面变化量达到本镜头中位数的 2 倍（且不低于 0.6 灰度级）也算画面事件
                                  # 短句开头前 0.3 秒到后 0.6 秒内要有画面事件或新字
LV = {'❌': 0, '⚠️': 1, 'ℹ️': 2}


def tick(name, t0): TIMING[name] = round(time.time() - t0, 1)


def sid_of(t):
    return next((s['id'] for s in reversed(ORDER) if s['t0'] <= t + 1e-6), ORDER[0]['id'])


def grab(pg, t, w):
    im = Image.open(io.BytesIO(snap(pg, max(0, min(TOTAL - 1e-3, t)), 85, w / FW))).convert('RGB')
    return im if im.size[0] == w else im.resize((w, round(w * FH / FW)), Image.BILINEAR)


def ranges(pg):
    return pg.evaluate('''(order) => {
      const TR = (window.PROJECT || {}).transitions || {};
      const trOf = i => { const s = order[i]; if (!order[i + 1]) return null; const v = TR[s.id] ?? TR.default ?? 'cut'; const o = typeof v === 'string' ? { type: v } : v; return o.type === 'cut' ? null : Object.assign({ dur: 0.5 }, o); };
      return order.map((S, i) => {
        const d = window.SHOT[S.id];
        let a = d && d.a !== undefined ? d.a : S.t0 - ((d && d.pre) || 0), z = d && d.b !== undefined ? d.b : S.t1 + ((d && d.post) || 0);
        const tin = i > 0 ? trOf(i - 1) : null, tout = trOf(i);
        if (tin) a = Math.min(a, S.t0 - tin.dur / 2);
        if (tout) z = Math.max(z, S.t1 + tout.dur / 2);
        return { id: S.id, a, z, tout };
      });
    }''', ORDER)


def strip(pg, ts, title, name):
    cells = [grab(pg, t, 300 if FW >= FH else 170) for t in ts]
    cw, ch = cells[0].size; sh = Image.new('RGB', (cw * len(cells), ch + 40), (30, 30, 30)); d = ImageDraw.Draw(sh)
    d.text((4, 3), title, fill=(120, 220, 255))
    for k, (t, c) in enumerate(zip(ts, cells)): sh.paste(c, (k * cw, 20)); d.text((k * cw + 4, ch + 24), f'{t:.2f}s', fill=(255, 220, 0))
    sh.save(OUT / name, quality=84); return name


def page_track(pg):
    """没有渲染时的登记：在页面上按草稿档帧率逐帧补一遍（不截图）"""
    fps = min(30, CFG.get('fps', 60)); n = int(round(TOTAL * fps)); frames = []
    pg.evaluate(TRACK_FLUSH_JS)
    for i in range(n):
        r = pg.evaluate(FRAME_JS, [i / fps, 0, 1, False, 30000])
        if r: frames.append(r[1])
    ex = pg.evaluate(TRACK_FLUSH_JS)
    g = pg.evaluate('(() => { const g = n => { try { return eval(n); } catch (e) { return null; } }; return [g("SHAKES"), g("FAST")]; })()')
    return dict(ex, fps=fps, size=[FW, FH], shakes=g[0] or [], fast=g[1] or [], frames=frames, segments=[[0, TOTAL]])


def text_appear(track):
    """每段字第一次出现的时刻（跨分段合并：上一段最后一帧还在、下一段第一帧接着在的，不算新出现）"""
    fps = track['fps']; segs = track.get('segments') or [[0, TOTAL]]
    seg_start = {round(a * fps) for a, z in segs}
    last = {}                                                        # (镜头, 字) → 最后出现的时刻
    out = []
    for sh, s, a, z in sorted(track.get('texts') or [], key=lambda x: x[2]):
        k = (sh, s); prev = last.get(k)
        cont = prev is not None and round(a * fps) in seg_start and abs(a - prev - 1 / fps) < 0.5 / fps
        if not cont and (prev is None or a - prev > 0.5): out.append((a, sh or sid_of(a), s))
        last[k] = max(z, prev or z)
    return out


# ---------------------------------------------------------------- 空帧（成片）
def empty_sheet(path, segs):
    """空帧.jpg：每段一格（那一段中间的一帧），标时段"""
    cells = [(a, z, frame_at(path, (a + z) / 2)) for a, z, *_ in segs[:12]]
    cells = [(a, z, im) for a, z, im in cells if im is not None]
    if not cells: return None
    cw = 380 if FW >= FH else 220; ch = round(cw * FH / FW); cols = min(4, len(cells)); rows = (len(cells) + cols - 1) // cols
    sh = Image.new('RGB', (cols * cw, rows * (ch + 22)), (26, 26, 26)); d = ImageDraw.Draw(sh); f = font(14)
    for k, (a, z, im) in enumerate(cells):
        x, y = (k % cols) * cw, (k // cols) * (ch + 22)
        sh.paste(im.resize((cw, ch), Image.LANCZOS), (x, y)); d.text((x + 4, y + ch + 3), f'{sid_of(a)}  {a:.1f}–{z:.1f}s', fill=(255, 220, 0), font=f)
    sh.save(OUT / '空帧.jpg', quality=84); return '空帧.jpg'


# ---------------------------------------------------------------- 图
def overview(per_shot, issues, subj_bad):
    """总览.jpg：每个镜头 2–3 帧，问题帧画框标编号。per_shot = {镜头: [(t, 图)]}"""
    k = max(len(v) for v in per_shot.values())
    cw = 250 if FW >= FH else 140; ch = round(cw * FH / FW); lab = 16
    per_row = max(1, (1600 // cw) // k); cols = per_row * k
    rows = (len(ORDER) + per_row - 1) // per_row
    sh = Image.new('RGB', (cols * cw + (per_row - 1) * 6, rows * (ch + lab + 6)), (26, 26, 26)); d = ImageDraw.Draw(sh); f = font(12); fb = font(13)
    by_shot = {}
    for it in issues:
        if it.get('n'): by_shot.setdefault(it['shot'], []).append(it)
    for j, S in enumerate(ORDER):
        r, c0 = divmod(j, per_row); x0 = c0 * (k * cw + 6); y0 = r * (ch + lab + 6)
        frames = per_shot.get(S['id'], [])
        for q, (t, im) in enumerate(frames):
            im = im.copy(); g = ImageDraw.Draw(im); x = x0 + q * cw; sc = cw / FW
            tags = []
            for it in by_shot.get(S['id'], []):
                ts = it.get('times') or [it.get('t')]
                near = min(range(len(frames)), key=lambda i: min(abs(frames[i][0] - (tt if isinstance(tt, (int, float)) else frames[i][0])) for tt in ts))
                if near != q: continue
                col = (235, 50, 50) if it['level'] == '❌' else (255, 190, 0)
                if it.get('box') and any(abs(tt - t) < 1e-3 for tt in ts if isinstance(tt, (int, float))):
                    b = it['box']; g.rectangle([b[0] * sc, b[1] * sc, b[2] * sc, b[3] * sc], outline=col, width=2)
                    g.rectangle([b[0] * sc, max(0, b[1] * sc - 14), b[0] * sc + 8 + 7 * len(str(it['n'])), max(14, b[1] * sc)], fill=col); g.text((b[0] * sc + 3, max(0, b[1] * sc - 14)), str(it['n']), fill=(0, 0, 0), font=f)
                else: tags.append((it['n'], col))
            if S['id'] in subj_bad: g.rectangle([0, 0, cw - 1, ch - 1], outline=(255, 190, 0), width=3)
            for m, (n, col) in enumerate(tags[:6]):
                g.rectangle([3 + m * 26, 3, 3 + m * 26 + 22, 19], fill=col); g.text((6 + m * 26, 4), str(n), fill=(0, 0, 0), font=f)
            sh.paste(im, (x, y0)); d.text((x + 3, y0 + ch + 1), f"{S['id']}  {t:.1f}s", fill=(255, 220, 0), font=fb)
    p = OUT / '总览.jpg'
    if sh.size[0] > 1600: sh = sh.resize((1600, round(sh.size[1] * 1600 / sh.size[0])), Image.LANCZOS)
    sh.save(p, quality=82); return p.name


def align_image(rows, curve, cfps):
    """对齐.jpg：每个镜头一条。rows = [(镜头, [(t0, t1, 文字, 有事件)], [(时刻, 名字)], [时刻])]"""
    Wd, lh = 1600, 74; f = font(12)
    im = Image.new('RGB', (Wd, lh * len(rows) + 22), (24, 24, 24)); d = ImageDraw.Draw(im)
    d.text((8, 4), '灰条 = 短句（红 = 这句话画面没有新事件）　蓝竖线 = act() 画面事件　黄三角 = 新出现的字　绿线 = 画面变化量（相邻帧差）', fill=(200, 200, 200), font=f)
    for j, (sid, phr, acts, texts) in enumerate(rows):
        S = TL['scenes'][sid]; a, z = S['t0'], S['t1']; y0 = 22 + j * lh; X = lambda t: 70 + (t - a) / max(1e-6, z - a) * (Wd - 80)
        d.rectangle([0, y0, Wd, y0 + lh - 2], fill=(34, 34, 34)); d.text((6, y0 + 4), sid, fill=(255, 220, 0), font=font(14)); d.text((6, y0 + 24), f'{a:.1f}–{z:.1f}s', fill=(150, 150, 150), font=f)
        if curve is not None:
            i0, i1 = int(a * cfps), min(len(curve), int(z * cfps))
            seg = curve[i0:i1]
            if len(seg) > 1:
                top = max(2.0, float(np.percentile(curve, 98)))           # 平方根缩放：切镜头的尖峰不把小动作压平
                pts = [(X(a + k / cfps), y0 + lh - 6 - min(1, math.sqrt(v / top)) * 34) for k, v in enumerate(seg)]
                d.line(pts, fill=(60, 200, 110), width=1)
        for t0, t1, txt, ok in phr:
            col = (90, 90, 90) if ok else (200, 60, 60)
            d.rectangle([X(t0), y0 + 6, max(X(t0) + 2, X(t1)), y0 + 20], fill=col); d.text((X(t0) + 2, y0 + 6), txt[:max(1, int((X(t1) - X(t0)) / 12))], fill=(240, 240, 240), font=f)
        for t, name in acts:
            if a - 0.5 <= t <= z: d.line([X(t), y0 + 22, X(t), y0 + lh - 4], fill=(80, 160, 255), width=2); d.text((X(t) + 2, y0 + 22), str(name)[:8], fill=(120, 180, 255), font=f)
        for t in texts:
            if a <= t <= z: d.polygon([(X(t) - 4, y0 + 30), (X(t) + 4, y0 + 30), (X(t), y0 + 38)], fill=(255, 210, 0))
    im.save(OUT / '对齐.jpg', quality=84); return '对齐.jpg'


# ---------------------------------------------------------------- 主流程
def main():
    issues, checks = [], []                                           # issue: dict(level, shot, t, times, src, text, kind, msg, box, img)
    def add(level, shot, t, kind, msg, text='', src=None, box=None, img=None, times=None):
        issues.append(dict(level=level, shot=shot, t=t, kind=kind, msg=msg, text=text, src=src, box=box, img=img, times=times or ([t] if isinstance(t, (int, float)) else [])))
    vpath = Path(VIDEO) if VIDEO else next((v for v in (ROOT / 'out' / out_name(FMT), ROOT / 'out' / out_name(FMT, '_draft')) if v.exists()), ROOT / 'out' / out_name(FMT))
    have_video = not NO_REVIEW and vpath.exists()
    # 成片体检（review.py）在后台先跑：它只读视频，和下面的页面检查同时进行
    rv_proc = subprocess.Popen([sys.executable, 'tools/review.py', str(vpath), '--format', FMT], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) if have_video else None
    # 空帧（读成片）和正式档重影比对（正式档才比）也在后台跑
    is_final = have_video and not vpath.stem.endswith('_draft')
    empty_res = {}
    def _empty():
        try: import motioncheck; empty_res['segs'] = motioncheck.empty_frames(vpath)
        except Exception as e: empty_res['err'] = str(e)[:300]
    empty_th = threading.Thread(target=_empty, daemon=True) if have_video else None
    if empty_th: empty_th.start()
    gh_json = OUT / 'ghost.json'
    gh_proc = subprocess.Popen([sys.executable, 'tools/ghostcheck.py', '--format', FMT, '--final', str(vpath), '--json', str(gh_json), '--outdir', str(OUT)],
                               cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) if is_final else None
    # 1 版面审计
    t0 = time.time(); lay_out = ''
    if LAYOUT and Path(LAYOUT).exists(): lay = json.load(open(LAYOUT))
    else:
        r = subprocess.run([sys.executable, 'tools/layout.py', 'checkup', '--format', FMT], cwd=ROOT, capture_output=True, text=True); lay_out = (r.stdout or '') + (r.stderr or '')
        jn = ROOT / 'frames' / '_view' / ('checkup' + (f'_{FMT}' if MULTI else '') + '_layout.json')
        lay = json.load(open(jn)) if jn.exists() else None
    tick('版面审计', t0)
    if lay is None:
        checks.append(('❌', '版面审计没跑完', '```\n' + lay_out[-1500:] + '\n```'))
        lay = {'items': [], 'deco': [], 'min_text': 0, 'n_samples': 0, 'override_ignored': None, 'subject': [], 'acts': [], 'fits': [], 'subject_min': SUBJECT_MIN['explainer']}
    for it in lay['items']:
        add(it['level'] if it['level'] in LV else 'ℹ️', it['shot'], it['times'][0], it['kind'], it['msg'], it['text'], it.get('src'), it.get('box'), times=it['times'])
    # 2 渲染时的登记
    track = None
    tp = Path(TRACK) if TRACK else ROOT / 'out' / 'segments' / f"full_{FMT}_{'draft' if vpath.stem.endswith('_draft') else 'final'}_track.json"
    if tp.exists(): track = json.load(open(tp))
    # 3 页面上的检查：开场、转场、总览帧、洋葱皮（没有登记时顺带补登记）
    lease = gpu_slot() if uses_gpu() else contextlib.nullcontext()
    with lease, sync_playwright() as p, serve() as url:
        b, pg, errs = open_page(p, url, FMT, init_script=TRACK_JS); pg.evaluate('window.__MB_OFF = true')
        R = ranges(pg)
        if track is None:
            t0 = time.time(); track = page_track(pg); tick('补登记（没有渲染时的登记）', t0)
        # 开场
        t0 = time.time(); fs = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        first = [(t, grab(pg, t, 320 if FW >= FH else 180)) for t in fs]
        empty = [t for t, im in first if content_stats(im, FW, FH)[2] < 0.0015]
        lvl = '❌' if len(empty) == len(fs) else '⚠️' if 0.0 in empty or len(empty) >= 3 else '✅'
        checks.append((lvl, '第一秒有主体', ('第一秒全程没有主体（画面是空的）' if lvl == '❌' else f'这些时刻画面是空的：{empty}' if empty else '0–1 秒每个取样点都有内容')))
        if lvl != '✅': add(lvl, ORDER[0]['id'], empty[0], '开场空画面', f'这些时刻画面是空的：{empty}')
        tick('第一秒', t0)
        # 转场叠化
        t0 = time.time(); fades, ovs = [], []
        for k in range(1, len(ORDER)):
            A, B = R[k - 1], R[k]; ov = A['z'] - B['a']; tr = A.get('tout')
            if tr and tr.get('type') == 'fade':
                c = ORDER[k]['t0']; ts = [c - tr['dur'] / 2 + tr['dur'] * j / 6 for j in range(7)]
                img = strip(pg, ts, f'{A["id"]} > {B["id"]}  fade {tr["dur"]}s', f'dissolve_{A["id"]}_{B["id"]}.jpg')
                fades.append(f'{A["id"]} → {B["id"]}'); add('ℹ️', A['id'], c, '通用 fade 转场', f'到 {B["id"]} 两层画面半透明叠化 {tr["dur"]} 秒：是想要的效果就保留', img=img)
            elif ov > 0.02:
                ts = [B['a'] + ov * j / 6 for j in range(7)]
                img = strip(pg, ts, f'{A["id"]} > {B["id"]}  both drawn {B["a"]:.2f}-{A["z"]:.2f}s', f'overlap_{A["id"]}_{B["id"]}.jpg')
                ovs.append(f'{A["id"]}→{B["id"]} {ov:.2f}s'); add('ℹ️', A['id'], B['a'], '镜头重叠段', f'和 {B["id"]} 同时在画 {ov:.2f} 秒：两层都半透明就是叠化，承接同一个元素就没问题', img=img)
        checks.append(('ℹ️' if fades else '✅', '通用 fade 转场（两层叠化）', f'{len(fades)} 处：{", ".join(fades)}' if fades else '没有'))
        checks.append(('ℹ️' if ovs else '✅', '镜头重叠段（可能是叠化）', f'{len(ovs)} 处：{", ".join(ovs[:10])}{" …" if len(ovs) > 10 else ""}' if ovs else '没有'))
        tick('转场', t0)
        # 总览帧：每个镜头取版面审计的 0.3 / 0.6 / 0.9 处（问题框的坐标就是这几刻的），镜头多时取 2 帧
        t0 = time.time(); k = 3 if len(ORDER) <= 16 else 2
        samp = {}
        for s in lay.get('subject') or []: samp.setdefault(s['shot'], []).append(s['t'])
        per_shot = {}
        cw = 250 if FW >= FH else 140
        for S in ORDER:
            std = [round(S['t0'] + f * S['dur'], 3) for f in ((0.3, 0.6, 0.9) if k == 3 else (0.3, 0.9))]
            ts = list(std)
            for it in issues:                                          # 有框的问题帧不在标准时刻上时，换掉最近的那一帧
                if it['shot'] == S['id'] and it.get('box') and it['times'] and not any(abs(it['times'][0] - x) < 1e-3 for x in ts):
                    j = min(range(len(ts)), key=lambda i: abs(ts[i] - it['times'][0]))
                    if ts[j] in std: ts[j] = it['times'][0]
            per_shot[S['id']] = [(t, grab(pg, t, cw)) for t in sorted(ts)]
        tick('总览帧', t0)
        # 洋葱皮：每个镜头一张，报告里只在要看运动的条目引用
        t0 = time.time(); sys.argv = ['stills.py', 'x', '--format', FMT]
        import stills; stills.FW, stills.FH = FW, FH
        tw = 640 if len(ORDER) <= 20 else 480; trails = {}
        for S in ORDER:
            a, z = S['t0'] + 0.05 * S['dur'], S['t0'] + 0.95 * S['dur']
            name = f'trail_{S["id"]}.jpg'; stills.trail_image(pg, a, z, 8, tw).save(OUT / name, quality=82); trails[S['id']] = name
        tick('洋葱皮', t0)
        b.close()
    # 4 文字块放不下（渲染时的登记补上版面取样没碰到的）
    seen = {(it['shot'], it['text']) for it in issues if it['kind'] == '文字块放不下'}
    for f in track.get('fits') or []:
        if (f.get('shot'), str(f.get('text', ''))[:24]) in seen: continue
        b_ = f.get('box') or {}; bw, bh = (b_.get('w', 0), b_.get('h', 0)) if isinstance(b_, dict) else (b_[2], b_[3]) if len(b_) >= 4 else (0, 0)
        add('ℹ️', f.get('shot') or sid_of(f.get('seen', 0)), f.get('seen', 0), '文字块放不下', f"box {bw:.0f}×{bh:.0f}px，照最小字号 {f.get('size', 0):.0f}px 画了，可能超出这块区域：要它待在区域里就删字、拆成两块，或给更大的 box", str(f.get('text', ''))[:24])
    # 5 主体大小
    smin = tuple(SUBJECT_MIN.get(GENRE, SUBJECT_MIN['explainer'])); subj = {}; subj_bad = set()
    for s in lay.get('subject') or []: subj.setdefault(s['shot'], []).append(s)
    for S in ORDER:
        v = subj.get(S['id'])
        if not v: continue
        cov = float(np.median([x['cov'] for x in v])); tx = float(np.median([x['text'] for x in v]))
        subj[S['id']] = (cov, tx)
        if cov < smin[0] and tx < smin[1]:
            subj_bad.add(S['id'])
            # 能照着改的量：取内容外框最大的取样点（按它放大，这个镜头的每一刻都放得下）
            gc, gr = lay.get('grid') or (16, 9)
            hints = [(x, *enlarge_hint(x['cells'], gc, gr)) for x in v if x.get('cells')]
            hints = [h_ for h_ in hints if h_[2]]
            pick = min(hints, key=lambda h_: h_[2]) if hints else None
            add('ℹ️', S['id'], pick[0]['t'] if pick else v[len(v) // 2]['t'], '主体偏小、留白多',
                f'内容覆盖 {cov * 100:.0f}%（参考 ≥ {smin[0] * 100:.0f}%），最大字高是短边的 {tx * 100:.1f}%（参考 ≥ {smin[1] * 100:.1f}%）' +
                (f'。{pick[0]["t"]:.1f}s 时{pick[1]}' if pick else ''))
    checks.append(('ℹ️' if subj_bad else '✅', '主体大小（内容覆盖 + 最大字高）', f'{len(subj_bad)} 个镜头两个都低：{", ".join(s for s in [x["id"] for x in ORDER] if s in subj_bad)}。可选提示里每条给出等比放大到几倍可占满安全区、哪一侧空；留白是设计时不用管；总览图里是橙色边框' if subj_bad else
                   f'每个镜头的内容覆盖 ≥ {smin[0] * 100:.0f}% 或最大字高 ≥ 短边 {smin[1] * 100:.1f}%'))
    # 6 讲解片：短句和画面事件对齐
    align = None
    acts = {(a.get('name'), a.get('at'), a.get('shot')): a for a in (track.get('acts') or []) + (lay.get('acts') or [])}
    appear = text_appear(track)
    if TL.get('mode') == 'voice':
        rows, no_ev = [], {}
        for S in ORDER:
            phr = []
            for ph in S.get('phrases') or []:
                a, z = ph['t0'] - ALIGN_PRE, ph['t0'] + ALIGN_POST
                ok = any(a <= float(x.get('at', -1e9)) - float(x.get('lead', 0) or 0) <= z for x in acts.values()) or any(a <= t <= z for t, _, _ in appear)
                phr.append((ph['t0'], ph['t1'], ph.get('text', ''), ok))
                if not ok: no_ev.setdefault(S['id'], []).append((ph['t0'], ph.get('text', '')))
            rows.append((S['id'], phr, [(float(x.get('at', 0)), x.get('name') or '') for x in acts.values() if x.get('shot') in (S['id'], None) or S['t0'] <= float(x.get('at', -1)) < S['t1']],
                         [t for t, sh, _ in appear if sh == S['id']]))
        align = {'rows': rows, 'no_ev': no_ev, 'acts': len(acts), 'text_appear': len(appear)}
    # 7 成片体检（review.py）
    rv = None; t0 = time.time()
    if NO_REVIEW: checks.append(('ℹ️', '成片体检', '按 --no-review 跳过（整帧刷灰、拍点空画面、单帧跳变、响度要渲完成片才查得到）'))
    elif not have_video: checks.append(('⚠️', '成片体检', f'没有成片 {vpath.name}，跳过。整帧刷灰、拍点空画面、单帧跳变、响度要渲完再跑一次 checkup'))
    else:
        rv_out = rv_proc.communicate()[0]
        rv = json.load(open(ROOT / 'out' / 'review.json')) if (ROOT / 'out' / 'review.json').exists() and rv_proc.returncode == 0 else None
        if rv:
            ws = rv.get('wash_list') or []
            checks.append(('ℹ️' if ws else '✅', '整帧被刷灰（成片）', f'{len(ws)} 处' if ws else '没有'))
            for w in ws: add('ℹ️', sid_of(w[0]), w[0], '整帧被刷灰', f'{w[1]} 帧，背景抬升 {w[2]}：叠化、闪白或半透明铺底都会这样')
            bl = rv.get('blank_beat_list') or []
            checks.append(('❌' if bl else '✅', '拍点空画面（成片）', f'{len(bl)} 处（同一帧只报一次），每处附逐帧条' if bl else '没有'))
            for x in bl:
                img = None
                if x.get('strip') and Path(x['strip']).exists(): img = Path(x['strip']).name; shutil.copy(x['strip'], OUT / img)
                add('❌', x['cut'] or sid_of(x['t']), x['t'], '拍点空画面', (f"{x['prev']} > {x['cut']} 的切点" if x['cut'] else '半拍') +
                    f"，空帧 {x['run'][0]:.2f}–{x['run'][1]:.2f}s 共 {x['n_blank']} 帧。{x['advice']}", img=img)
            v = rv.get('pop_times') or []
            checks.append(('❌' if v else '✅', '单帧跳变（成片）', f'{len(v)} 处' if v else '没有'))
            for t in v: add('❌', sid_of(t), t, '单帧跳变', '某个元素只闪了一帧')
            for k_, nm, lo, hi in (('loudness', '响度 LUFS', -16 if GENRE == 'promo' else -20, -12 if GENRE == 'promo' else -14), ('true_peak', '真峰值 dBFS', None, -0.5)):
                if rv.get(k_) is not None:
                    ok = (lo is None or rv[k_] >= lo) and rv[k_] <= hi
                    checks.append(('✅' if ok else '⚠️', nm + '（成片）', f'{rv[k_]}'))
        else: checks.append(('❌', '成片体检没跑完', '```\n' + (rv_out or '')[-1500:] + '\n```'))
    tick('成片体检', t0)
    # 6b 短句对齐收尾：成片里这句开头附近画面有明显变化（物件动了、换了画面），也算有事件
    if align is not None:
        rows, no_ev = align['rows'], align['no_ev']
        cv = np.array(rv['diff_series']) if rv and rv.get('diff_series') else None
        if cv is not None and len(cv):
            cfps = rv.get('fps', 30)
            def moved(t, S):
                i0, i1 = int(S['t0'] * cfps), max(int(S['t0'] * cfps) + 1, int(S['t1'] * cfps))
                base = float(np.median(cv[i0:i1])) if i1 > i0 else float(np.median(cv))
                j0, j1 = max(0, int((t - ALIGN_PRE) * cfps)), min(len(cv), int((t + ALIGN_POST) * cfps) + 1)
                return j1 > j0 and float(cv[j0:j1].max()) >= max(MOTION_EVENT_K * base, MOTION_EVENT_MIN)
            by_id = {S['id']: S for S in ORDER}
            for sid in list(no_ev):
                no_ev[sid] = [(t, x) for t, x in no_ev[sid] if not moved(t, by_id[sid])]
                if not no_ev[sid]: del no_ev[sid]
            bad_t = {(sid, round(t, 3)) for sid, L in no_ev.items() for t, _ in L}
            rows = [(sid, [(t0_, t1_, x, (sid, round(t0_, 3)) not in bad_t) for t0_, t1_, x, _ in phr], ev, ap) for sid, phr, ev, ap in rows]
        for sid, L in no_ev.items():
            add('ℹ️', sid, L[0][0], '这句话画面没有新事件', '；'.join(f'{t:.1f}s「{x[:14]}」' for t, x in L[:4]) + (f' …共 {len(L)} 句' if len(L) > 4 else ''), times=[t for t, _ in L])
        n_ph = sum(len(r[1]) for r in rows); n_bad = sum(len(v) for v in no_ev.values())
        align = {'phrases': n_ph, 'no_event': n_bad, 'acts': len(acts), 'text_appear': len(appear), 'rows': rows}
        checks.append(('ℹ️' if n_bad else '✅', '短句和画面事件对齐（讲解片）', f'{n_bad}/{n_ph} 句开头前 {ALIGN_PRE} 秒到后 {ALIGN_POST} 秒内既没有 act() 事件，也没有新的字出现，成片里画面也没有明显变化（act() 登记 {len(acts)} 个，新出现的字 {len(appear)} 处）。不要求每句都有。图：对齐.jpg'))

    # 7a 文字互相压住（渲染时逐帧查的，补上版面取样点碰不到的短暂重叠：换句时前一段没退完、后一段已进来，不到 0.5 秒）
    seen_pairs = {(it['shot'], it['text'][:12]) for it in issues if it['kind'] == '文字互相压住'}
    fps_ = track.get('fps') or 30; ovl = {}
    for o in track.get('overlaps') or []:                              # 跨分段的同一对合并
        k = (o.get('shot'), o['a'], o['b']); e = ovl.get(k)
        if e and o['t0'] - e['t1'] <= 1.5 / fps_: e['t1'] = max(e['t1'], o['t1']); e['n'] += o['n']
        elif not e or o['t0'] < e['t0']: ovl[k] = dict(o)
    groups = []                                                      # 同一镜头、时间相接的合并成一处（逐字动画会有很多对字）
    for (sh_, a_, b_), o in sorted(ovl.items(), key=lambda kv: kv[1]['t0']):
        sh_ = sh_ or sid_of(o['t0'])
        if (sh_, a_[:12]) in seen_pairs or (sh_, b_[:12]) in seen_pairs: continue
        if o['t1'] - o['t0'] + 1 / fps_ >= 0.5: continue               # 长时间的重叠交给版面审计（它会算卡片的遮挡）；这里只补短暂的
        g = groups[-1] if groups and groups[-1]['shot'] == sh_ and o['t0'] <= groups[-1]['t1'] + 0.2 else None
        if g is None: g = dict(shot=sh_, t0=o['t0'], t1=o['t1'], a=[], b=[], box=list(o.get('box') or [0, 0, 0, 0])); groups.append(g)
        g['t1'] = max(g['t1'], o['t1'])
        for k_, v_ in (('a', a_), ('b', b_)):
            if v_ not in g[k_]: g[k_].append(v_)
        if o.get('box'): bx = o['box']; g['box'] = [min(g['box'][0], bx[0]), min(g['box'][1], bx[1]), max(g['box'][2], bx[2]), max(g['box'][3], bx[3])]
    for g in groups:
        ta, tb = ''.join(g['a'])[:12], ''.join(g['b'])[:12]
        add('⚠️', g['shot'], g['t0'], '文字互相压住', f'「{ta}」和「{tb}」短暂叠在一起，{g["t0"]:.2f}–{g["t1"] + 1 / fps_:.2f}s：'
            '换句时前一段还没退完、后一段已经进来。让前一段先退完，或后一段晚一点入场', ta, box=g['box'], times=[g['t0']])
    # 7b 同框文字冲突（渲染时引擎登记的 __TEXTCLASH）
    clash = {}
    for c in track.get('clash') or []:
        k = (c.get('shot'), c.get('a'), c.get('b'))
        if k not in clash or c.get('t', 0) < clash[k].get('t', 0): clash[k] = c
    for (sh_, a_, b_), c in sorted(clash.items(), key=lambda kv: kv[1].get('t', 0)):
        t_ = float(c.get('t', c.get('seen', 0)))
        if float(c.get('delay') or 0) > 0:                             # 引擎已推迟后一段：画面上没叠，只提示看时机
            add('ℹ️', sh_ or sid_of(t_), t_, '同框换句已自动推迟', f'同一个框里两段字原定同时可见，后一段已推迟 {float(c["delay"]):.2f} 秒到前一段退完：「{str(a_)[:16]}」→「{str(b_)[:16]}」。'
                '确认推迟后还对得上配音；要两段衔接，就让前一段早点退场', str(b_)[:24])
        else:                                                          # 推迟不了：两段字叠在同一个框里
            add('⚠️', sh_ or sid_of(t_), t_, '文字互相压住', f'同一个框里两段字同时可见、叠在一起：「{str(a_)[:16]}」和「{str(b_)[:16]}」。'
                '让前一段先退场（o.out），或给它们不同的框', str(b_)[:24])
    n_delay = sum(1 for c in clash.values() if float(c.get('delay') or 0) > 0)
    checks.append(('⚠️' if len(clash) > n_delay else 'ℹ️' if clash else '✅', '同框文字冲突',
                   (f'{len(clash) - n_delay} 处叠在一起；' if len(clash) > n_delay else '') + (f'{n_delay} 处后一段已自动推迟，看时机还对不对' if n_delay else '') if clash else '没有'))
    # 7c 空帧（成片）
    if empty_th:
        empty_th.join()
        if 'err' in empty_res: checks.append(('⚠️', '空帧（成片）', '没跑完：' + empty_res['err']))
        else:
            segs = empty_res['segs']; img = empty_sheet(vpath, segs) if segs else None
            for a_, z_, m_, k_ in segs:
                if k_ == '整屏色块':
                    add('⚠️', sid_of(a_), a_, '空帧', f'{a_:.1f}–{z_:.1f}s 满屏一块颜色或渐变、上面没有内容（{z_ - a_:.1f} 秒）：多半是转场色块停住了。色块转场要在 0.3 秒内扫过，'
                        '或在色块上放下一组内容；是有意的色场就在交付说明里写一句', img=img, times=[a_, z_])
                    continue
                add('⚠️', sid_of(a_), a_, '空帧', f'{a_:.1f}–{z_:.1f}s 画面几乎只剩背景（偏离背景的像素最少 {m_ * 100:.1f}%）：上一组内容退完、下一组还没进来。'
                    '是设计的留白（一句话前的停顿、落版的呼吸）就在交付说明里写一句；否则让下一组提前入场，或让上一组留到下一组进来', img=img, times=[a_, z_])
            checks.append(('⚠️' if segs else '✅', '空帧（成片）', f'{len(segs)} 段：' + '、'.join(f'{a_:.1f}–{z_:.1f}s' + ('（整屏色块）' if k_ == '整屏色块' else '') for a_, z_, _, k_ in segs[:8]) + '。图：空帧.jpg' if segs else '没有'))
    # 7d 正式档重影（和草稿档逐帧比）
    if gh_proc:
        gh_out = gh_proc.communicate()[0]
        g = json.load(open(gh_json)) if gh_json.exists() else None
        if g is None: checks.append(('⚠️', '正式档重影（和草稿档比对）', '没跑完：\n```\n' + (gh_out or '')[-1200:] + '\n```'))
        elif g['status'] != 'ok': checks.append(('ℹ️', '正式档重影（和草稿档比对）', g['reason']))
        else:
            for x in g['found']:
                add('❌', sid_of(x['peak_t']), x['peak_t'], '正式档重影', f"{x['t_start']:.2f}–{x['t_end']:.2f}s 文字或物体出现错开的副本（新边缘占比 {x['score']:.2f}，草稿档同一时刻干净）："
                    '这段运动太快、运动模糊的采样不够。调高 project.json 的 motion_blur.max，或用 FAST 登记这一段并给更大的采样数，也可以放慢这段运动',
                    img=Path(x['image']).name if x.get('image') else None, times=[x['t_start'], x['t_end']])
            checks.append(('❌' if g['found'] else '✅', '正式档重影（和草稿档比对）', f"比了 {g['frames']} 帧（在动的 {g['compared']} 帧）：" +
                           (f"{len(g['found'])} 处，图 ghost_N.jpg（左正式档、右草稿档）" if g['found'] else '没有')))
    elif have_video: checks.append(('ℹ️', '正式档重影（和草稿档比对）', '体检的是草稿档；正式档出完后自动比对'))

    # 8 静止段、时长、抖动
    t0 = time.time(); mres = None
    shots = [(S['id'], S['t0'], S['t1'], S.get('motion', '稳')) for S in ORDER]
    if have_video:
        import motioncheck
        tgt = CFG.get('target_sec')
        mres = motioncheck.check(vpath, float(tgt) if tgt else None, 2.0 if GENRE == 'promo' else 3.0, shots=shots, track=track, U=min(FW, FH) / 1080)
        for lv, name, note in motioncheck.lines(mres): checks.append((lv, name + '（成片）', note))
        for a, z, d in mres['still_runs']: add('ℹ️', sid_of(a), a, '画面停住', f'{a}–{z}s（{d} 秒）：让观众读完、消化就保留，内容在空等就推进')
        if mres.get('duration_off') is not None and not mres['duration_ok']: add('❌', '全片', 0.0, '时长对目标', f'成片 {mres["duration"]} 秒，目标 {mres["target"]:g} 秒，差 {mres["duration_off"] * 100:+.0f}%')
    else:
        import motioncheck
        jb, lb, has = motioncheck.track_motion(track, shots, min(FW, FH) / 1080)
        lab = {i: g for i, a, b, g in shots}
        mres = {'jitter': [dict(a=a, b=b, n=n, shot=s, kind=k_, tag=lab.get(s, '稳')) for a, b, n, s, k_ in jb], 'shake_long': [dict(a=a, b=b, shot=s) for a, b, s in lb],
                'shake_shots': [i for i, a, b, g in shots if g == '可以震'], 'n_shots': len(shots), 'track': True, 'track_has_cams': has, 'still_runs': []}
        if CFG.get('target_sec'):
            off = (TOTAL - float(CFG['target_sec'])) / float(CFG['target_sec'])
            checks.append(('❌' if abs(off) > 0.10 else '✅', '时间轴总长对目标', f'{TOTAL:.1f} 秒，目标 {CFG["target_sec"]} 秒，差 {off * 100:+.0f}%'))
    for r in mres.get('jitter') or []:
        add('⚠️' if r['tag'] == '稳' and r['kind'] == '快抖' else 'ℹ️', r['shot'], r['a'], '画面抖动', f"{r['a']:g}–{r['b']:g}s 镜头{r['kind']}，反向 {r['n']} 次（「{r['tag']}」镜头）", img=trails.get(r['shot']), times=[r['a'], r['b']])
    for r in mres.get('shake_long') or []:
        add('ℹ️', r['shot'], r['a'], '单次震动太长', f"{r['a']:g}–{r['b']:g}s 连续快抖超过 0.5 秒：震屏要短促", img=trails.get(r['shot']))
    ss, n_ = mres.get('shake_shots') or [], len(ORDER)
    if ss and len(ss) > n_ / 3: add('ℹ️', '全片', 0.0, '「可以震」镜头偏多', f'{len(ss)}/{n_} 个镜头标了「可以震」：{", ".join(ss)}。震屏只给撞击、惊喜、重拍这类瞬间')
    tick('静止、时长与抖动', t0)
    # 9 编号、总览图、对齐图
    issues.sort(key=lambda x: (LV.get(x['level'], 3), x['times'][0] if x['times'] else 0))
    n = 0
    for it in issues:
        if it['level'] in ('❌', '⚠️'): n += 1; it['n'] = n
        tt = it['t'] if isinstance(it['t'], (int, float)) else 0
        it['line'] = (f"{it['n']}. " if it.get('n') else '') + fmt_line(it['level'], it['shot'], tt, it['src'], it['text'], it['kind'], it['msg'], len(it['times']) if it['kind'] not in ('画面抖动', '这句话画面没有新事件', '空帧', '正式档重影') else 1) + (f'　图：{it["img"]}' if it.get('img') else '')
    t0 = time.time(); ov = overview(per_shot, issues, subj_bad)
    if align:
        cv = rv.get('diff_series') if rv else None
        align_image(align['rows'], np.array(cv) if cv else None, rv.get('fps', 30) if rv else 30)
    tick('总览图', t0)
    # 10 报告
    cnt = {}
    for it in issues: cnt[it['kind']] = cnt.get(it['kind'], 0) + 1
    for kind, lv, why in (('字太小', '❌', ''), ('文字出框', '❌', ''), ('文字互相压住', '❌', ''),
                          ('标注没落到目标', '❌', '引线终点要落在 anchor 登记的目标上'),
                          ('线穿过文字', '⚠️', '线从一段字的字身上穿过去，读不清；绕开或把字挪开'),
                          ('占位字', '⚠️', '片子没做完：换成真实内容或删掉'),
                          ('文字块放不下', 'ℹ️', '照最小字号画了；真的出框、压字由上面两项报'),
                          ('线头悬空', 'ℹ️', '两端都没碰到别的元素，多半是手填坐标没对上目标；可以改用 anchor + callout'),
                          ('过程标注词', 'ℹ️', '时长、片型、示意、版本这类词观众多半用不上'),
                          ('直接用 fillText 画的字', 'ℹ️', '出框、字号、压字照样查')) + (
                          (('画面内容进了字幕带', '⚠️', '字幕开着时 safeBox() 已让出字幕带，画面里的字和讲解的目标放在它以内；背景进字幕带不算'),) if subtitles(CFG)['burn'] else ()):
        c = cnt.get(kind, 0)
        if c: lv = min((it['level'] for it in issues if it['kind'] == kind), key=lambda x: LV.get(x, 3))   # 按实际条目里最重的一级
        checks.insert(0, ('✅' if not c else lv, kind, f'{c} 处（按镜头合并后）' + (f'；字号下限 {lay["min_text"]:.0f}px（短边成比例，锁定）' if kind == '字太小' else '') + (f'。{why}' if c and why else '')))
    if lay.get('override_ignored') is not None:
        checks.append(('⚠️', 'project.json 的 layout.min_text 已不生效', f'写了 {lay["override_ignored"]}，下限仍是 {lay["min_text"]:.0f}px。删掉这一项；要小字就逐个标 deco。'))
    checks.append(('ℹ️' if lay['deco'] else '✅', '装饰字豁免', f'{len(lay["deco"])} 条，全部列在下面「装饰字豁免」一节'))
    nb = sum(1 for x in issues if x['level'] == '❌'); nw = sum(1 for x in issues if x['level'] == '⚠️')
    info = [it for it in issues if not it.get('n')]
    L = ['# 体检报告', '',
         '> **全部通过只说明没有观众看得见的硬伤。** 片子到哪个档位，要看成片定：讲没讲清楚、节奏、主角、动作好不好看，这些检查都量不出来。', '',
         f'{FW}×{FH} · {TOTAL:.1f} 秒 · {len(ORDER)} 个镜头 · 片型 {GENRE} · 字号下限 {lay["min_text"]:.0f}px · 版面取样 {lay.get("n_samples", 0)} 个时刻 · 用时 {time.time() - T_START:.0f} 秒', '',
         f'**{summary_line(nb, nw, len(info), "下面「可选提示」一节")}。** 先看问题清单和 `总览.jpg`（编号对应）' + ('、`对齐.jpg`' if align else '') + '。', '',
         '## 问题清单', '', '观众看得见的硬伤：❌ 要改，⚠️ 打开总览图上对应编号看一眼再决定。', '']
    L += [it['line'] for it in issues if it.get('n')] or ['没有硬伤。']
    L += ['', '## 可选提示', '', '不算问题，按片子的设计决定改不改：留白、停顿、镜头运动、转场方式都是设计选择。看不懂、显得空的时候可以回来对照。', '']
    L += ['- ' + it['line'] for it in info[:40]] + ([f'- …还有 {len(info) - 40} 条，见 checkup.json'] if len(info) > 40 else []) if info else ['没有。']
    L += ['', '## 各项检查', '', '❌ 硬伤，要改　⚠️ 硬伤，看一眼再决定　ℹ️ 可选提示　✅ 通过', '']
    L += [f'- {lv} **{name}**：{note}' for lv, name, note in checks]
    L += ['', '## 按镜头', '', '| 镜头 | 时段（秒） | 内容覆盖 | 最大字高（短边 %） | 问题编号 |', '|---|---|---|---|---|']
    for S in ORDER:
        c = subj.get(S['id']); ns = [str(it['n']) for it in issues if it.get('n') and it['shot'] == S['id']]
        cv_ = f"{c[0] * 100:.0f}%" if isinstance(c, tuple) else '—'; tx_ = f"{c[1] * 100:.1f}" if isinstance(c, tuple) else '—'
        L.append(f"| {S['id']} | {S['t0']:.1f}–{S['t1']:.1f} | {cv_}{' ⚠️' if S['id'] in subj_bad else ''} | {tx_} | {', '.join(ns) or '—'} |")
    L += ['', f'内容覆盖：画面约 144 格里墨量够的格子占比；最大字高：观众要读的字里最大的字高（常驻页眉角标不算）。两个都低于 {smin[0] * 100:.0f}% / {smin[1] * 100:.1f}% 才报。', '']
    L += ['## 装饰字豁免', '', '这些字标了 deco，不按字号下限检查。确认它们真的不需要被读到：观众要读的字不能标装饰字。', '']
    if lay['deco']:
        L += ['| 镜头 | 文字 | 字高 px | 原因 | 时刻 |', '|---|---|---|---|---|']
        for d in lay['deco']: L.append(f"| {d['shot']} | {d['text']} | {d['cap']} | {d['why']} | {' '.join(f'{t:.2f}' for t in d['times'][:4])} |")
    else: L.append('没有。')
    L += ['', '## 图', '', f'- {ov}：每个镜头 {k} 帧，问题帧画框、标编号；橙色边框 = 主体偏小、留白多']
    if align: L.append('- 对齐.jpg：每个镜头一条：短句（红 = 没有新事件）、act() 事件、新出现的字、画面变化量')
    L.append('- trail_<镜头>.jpg：洋葱皮，8 帧叠在一起（越新越实）。看轨迹顺不顺、残影间距是不是先密后疏')
    if any(f.name.startswith(('overlap_', 'dissolve_')) for f in OUT.iterdir()): L.append('- overlap_*.jpg / dissolve_*.jpg：两个镜头同时在画的那段，等距 7 帧')
    if (OUT / '空帧.jpg').exists(): L.append('- 空帧.jpg：每段空帧中间的一帧，标时段')
    if any(f.name.startswith('ghost_') and f.suffix == '.jpg' for f in OUT.iterdir()): L.append('- ghost_N.jpg：正式档重影峰值那一帧，左正式档、右草稿档')
    if rv: L.append('- 成片总览：frames/_view/review_NN.jpg（review.py 生成，每 0.5 秒一帧）')
    L += ['', f'各步用时（秒）：{TIMING}', '']
    (OUT / '报告.md').write_text('\n'.join(L), encoding='utf-8')
    for it in issues: it.pop('box_img', None)
    json.dump({'report': str(OUT / '报告.md'), 'overview': str(OUT / ov), 'align': str(OUT / '对齐.jpg') if align else None, 'video': str(vpath),
               'issues': issues, 'checks': checks, 'subject': {k_: v for k_, v in subj.items() if isinstance(v, tuple)}, 'subject_min': smin,
               'align': {k_: v for k_, v in (align or {}).items() if k_ != 'rows'} or None, 'motion': mres, 'timing': TIMING,
               'total_sec': TOTAL, 'shots': len(ORDER), 'elapsed': round(time.time() - T_START, 1)}, open(OUT / 'checkup.json', 'w'), ensure_ascii=False, indent=1)
    print(summary_line(nb, nw, len(info)))
    for it in [x for x in issues if x.get('n')][:30]: print(it['line'])
    print(f'\n报告：{OUT / "报告.md"}　总览图：{OUT / ov}（用时 {time.time() - T_START:.0f} 秒）')


if __name__ == '__main__':
    main()
    sys.stdout.flush(); import os; os._exit(0)      # 结果已落盘；杀掉 Chrome 后 Playwright 收尾偶尔要等约 30 秒，直接退出
