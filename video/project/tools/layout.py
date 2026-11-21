"""版面审计（不用渲整片，直接在页面上跑）：python3 tools/layout.py [名字] [--format 名字|all]
用途：渲整片之前，先查出观众看得见的版面硬伤：字太小、字出框、字压字、标注没指到目标。静帧自查只靠肉眼，小字、轻微出框、差几像素的线头很容易漏。
做法：包装画布的画字（fillText / strokeText）和画线、画形状（moveTo / lineTo / arc / 曲线 / rect + stroke / fill、fillRect、drawImage），
      记录屏幕坐标（已算上当前变换矩阵，也就是镜头推近、漂移、转场位移）；每个镜头取 0.3 / 0.6 / 0.9 处，节拍片再加每一拍，逐点渲染并检查。
      直接调 ctx.fillText 画的字和经 txt()、textBlock 画的字一样量；画在离屏画布上再贴进来的字量不到。
检查分两级（宣传片和讲解片同一套，阈值是默认值）。硬伤进终端摘要和问题条数；可选提示只写进报告，不算问题，版式怎么做由片子自己定。
硬伤：
  ❌ 字太小    透明度 ≥ 0.6 的文字，屏幕字高（同字体 H 的高度，即大写字母高度）小于可读下限。宣传片 短边 × 0.022（1080p 约 24 像素，信息流里一眼读完）；
              讲解片 短边 × 0.015（约 16 像素，观众有阅读时间）。下限锁定，不能在 project.json 里调低。刻意的小字在绘制时标 deco（见 core.js 的 deco），
              不按下限查，但逐条列进报告。
  ❌ 文字出框  外框离画面边缘不到半个安全区边距（短边 × 2.5%，按屏幕坐标）。完全在画面外的不算（还没入场）；装饰字不算。
              报告里附这一刻的镜头变换（cam 的中心和缩放），一眼看出是不是被推近推出去的。
  ❌ 文字互相压住  同一段字在同一位置的重复绘制（描边 + 填充、投影）先合并成一个外框；再把同字体、同基线（±2 像素）、水平间距小于 0.6 个字高的
              连续调用合并成一行，查不同行外框相交（交集占小框面积 > 3%）。两行透明度都 ≥ 0.5 报 ❌；有一行在 0.3–0.5（淡入淡出中、被调暗的字）报 ⚠️。
              先画的那行被画在两行之间的不透明填充（透明度 ≥ 0.8，例如卡片）盖住相交处的不算。只报 0.15 秒后仍然压在一起的；
              更短的（换句时前一段没退完、后一段已进来）由渲染时逐帧登记查（common.py 的 TRACK_JS），体检报出。
  ❌ 标注没落到目标  读 core.js 的 callout 记下的引线（window.__LINKS）和 anchor 登记的目标（window.__ANCHORS，画布像素）：长完的引线（p = 1）
              终点不在目标矩形内或边缘 4 像素以内，或者目标这一帧没有登记（callout 会在控制台警告），就报。用 callout 画的标注，终点由引擎算出，镜头怎么动都跟得上。
  ⚠️ 线穿过文字  线条（透明度 ≥ 0.45、线宽 ≥ 1.5 像素）穿过一段字的字身（外框上下各收 20%），而这段字不是这条线端点所在的标签；
              线画完后又被不透明的形状盖住的那一截不算；伸出画面的线（地平线、背景线条）不算。只报 0.15 秒后仍然穿过的。
  ⚠️ 画面内容进了字幕带  project.json 开了字幕层（引擎登记 window.__SUBS = {on, langs, box}，on 为真）时，字幕带 box 里出现了要让观众看的东西：
              非字幕的字（透明度 ≥ 0.5、非装饰字）外框有 20% 以上落在字幕带里；或 anchor() 登记的目标（讲解的主体部位）有 30% 以上落在字幕带里。
              只报 0.15 秒后仍然在带里的。背景、地面、底色这类填充进字幕带不报：推近镜头时它们被推进字幕带是正常的，字幕有底色光晕读得清。
              没用 anchor() 登记的形状量不到，主体靠近字幕带时看静帧。字幕开着时 safeBox() 已让出字幕带。
              字幕的字（引擎画字幕时 ctx.__role = 'subtitle'）不参与「文字互相压住」「线穿过文字」「过程标注词」和最大字高，只查字太小和出框。
  ⚠️ 占位字    没换掉的占位字（「YOUR NAME」「Your Logo」「LOGO HERE」「Lorem ipsum」「TBD」「XXX」「公司名」「品牌名」等，大小写不敏感）：片子没做完。
可选提示（ℹ️）：
  ℹ️ 文字块放不下  textBlock() 用最小字号也放不进给它的 box（引擎往 window.__TEXTFIT 登记），字照最小字号画了，可能超出这块区域。
              真的出框、压字由上面的硬伤检查报。
  ℹ️ 线头悬空  描边的开放斜线、曲线（长于 12 像素；水平或竖直的直线不查），两个端点都没碰到别的东西：文字框、图片框、填充或描边图形的外框、锚点、
              别的线（4 像素 + 半个线宽以内，或和别的线相交）。伸出画面的一端算连上；贴着文字的下划线、删除线算连上。
              4 个以上显式顶点的开放折线、曲线是数据线或轨迹，不查。只报 0.15 秒后还在原处悬空的。多半是手填坐标没对上目标，可以改用 anchor + callout。
  ℹ️ 过程标注词  画面文字里出现「15 SECONDS」「EXPLAINED」「示意」「DEMO」「v2.1」「版本」这类词：时长、片型、示意、版本观众多半用不上。
  ℹ️ 直接用 fillText 画的字  整片合并成一条：出框、字号、压字照样查；要标装饰小字时用 deco(ctx, 原因, () => …) 包起来。
主体大小（结果交给 checkup.py 按镜头判定，阈值见下面 SUBJECT_MIN）：每个取样点量两个数。
  内容覆盖  画面分成约 144 格（16×9；竖版 9×16；方形 12×12），按和背景的色差算每格的墨量，墨量够的格子占比。细线、暗淡的框、小字只占很少。
  最大字高  这一刻观众要读的字里最大的字高 / 短边。常驻的页眉角标（同一位置、同样字高出现在 3 个以上镜头）是导航，不算。
  两个都低的镜头，checkup 在可选提示里写「主体偏小、留白多」，并给出能照着改的量：内容外框（有内容的格子的外接矩形）占安全区多少、
  等比放大到约几倍可占满安全区（一个方向已铺满时，给另一个方向能放大几倍）（enlarge_hint），以及最大的空白在哪一侧（例如「下半幅空」）。
每条问题一行，带镜头文件的行号（包装画字、画线时取调用栈里第一个 shots_*.js 的帧）：
  ❌ S05 · 12.3s · web/shots_05.js:27 · 「几十年内」 · 文字出框（右侧超出画面 18px）
输出：终端摘要（只列硬伤）＋ frames/_view/<名字>_layout.jpg（问题帧缩略图，红框 = 文字问题，品红 = 线的问题）＋ frames/_view/<名字>_layout.json（全部条目、主体取样、画面事件、放不下的文字块）。
不在检查范围内：画在离屏画布上再贴进来的字和线（例如 appWindow 里的截图），用 Path2D 对象画的线。
"""
import sys, os, io, re, json, math, contextlib
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from common import ROOT, serve, open_page, timeline, pop_format, formats, project, uses_gpu, gpu_slot, out_name, snap

INIT_JS = r"""
(() => {
  window.__TXT = []; window.__LINES = []; window.__SHAPES = []; window.__SEQ = 0; window.__REC = false; window.__CAMNOW = null;
  const P = CanvasRenderingContext2D.prototype, capCache = {}, MAXN = 6000;
  Error.stackTraceLimit = 40;
  // 调用栈里第一个 shots_*.js 的帧 → 'web/shots_05.js:27'（问题定位到镜头文件的那一行）
  const srcOf = st => { const m = /\/(shots_[^\/:?#\s)]+\.js)(?:\?[^:\s)]*)?:(\d+):\d+/.exec(st || ''); return m ? 'web/' + m[1] + ':' + m[2] : null; };
  window.__SRCOF = srcOf;
  const alphaOf = c => {
    if (typeof c !== 'string') return 1; c = c.trim();
    if (c === 'transparent') return 0;
    let m = /^(?:rgba|hsla)\(([^)]*)\)$/.exec(c); if (m) { const p = m[1].split(/[,\/\s]+/).filter(Boolean); return p.length >= 4 ? parseFloat(p[3]) * (p[3].endsWith('%') ? 0.01 : 1) : 1; }
    m = /^#([0-9a-f]{8}|[0-9a-f]{4})$/i.exec(c); if (m) { const h = m[1]; return h.length === 8 ? parseInt(h.slice(6), 16) / 255 : parseInt(h[3] + h[3], 16) / 255; }
    return 1;
  };
  const shotNow = () => { try { return typeof SHOT_NOW !== 'undefined' ? SHOT_NOW : null; } catch (e) { return null; } };
  const on = c => window.__REC && c.canvas && c.canvas.id === 'c';
  const tp = (T, x, y) => [T.a * x + T.c * y + T.e, T.b * x + T.d * y + T.f];
  const camOf = T => ({ s: Math.sqrt(Math.abs(T.a * T.d - T.b * T.c)), e: T.e, f: T.f, cam: window.__CAMNOW });
  const wrap = (name, fn) => { const o = P[name]; if (!o) return; P[name] = function () { if (on(this)) { try { fn.apply(this, arguments); } catch (e) {} } return o.apply(this, arguments); }; };
  // ---------------- 文字
  for (const name of ['fillText', 'strokeText']) {
    wrap(name, function (s, x, y) {
      const str = String(s); if (!str.trim() || window.__TXT.length >= MAXN) return;
      const m = this.measureText(str), font = this.font + '|' + this.textBaseline;
      if (capCache[font] === undefined) { const h = this.measureText('H'); capCache[font] = h.actualBoundingBoxAscent + h.actualBoundingBoxDescent; }
      const T = this.getTransform(), sy = Math.hypot(T.c, T.d);
      const full = new Error().stack || '', st = full.split('\n').slice(3, 4).join(''), raw = /shots_[^/]*\.js/.test(st);
      const px = /(\d+(?:\.\d+)?)px/.exec(this.font);
      const xs = [x - m.actualBoundingBoxLeft, x + m.actualBoundingBoxRight], ys = [y - m.actualBoundingBoxAscent, y + m.actualBoundingBoxDescent];
      const X = [], Y = [];
      for (const a of xs) for (const b of ys) { const q = tp(T, a, b); X.push(q[0]); Y.push(q[1]); }
      window.__TXT.push({ s: str, x0: Math.min(...X), y0: Math.min(...Y), x1: Math.max(...X), y1: Math.max(...Y), kind: name === 'fillText' ? 'fill' : 'stroke',
        ay: T.b * x + T.d * y + T.f, deco: this.__deco || null, role: this.__role || null, fs: (px ? parseFloat(px[1]) : 0) * sy, cap: capCache[font] * sy, font, raw,
        a: this.globalAlpha * alphaOf(name === 'fillText' ? this.fillStyle : this.strokeStyle), seq: window.__SEQ++, shot: shotNow(), m: camOf(T), src: srcOf(full) });
    });
  }
  // ---------------- 路径：按子路径记屏幕坐标
  const cur = c => { const L = c.__P || (c.__P = []); return L[L.length - 1]; };
  // v = 显式顶点数（moveTo 和每次 lineTo / 曲线终点各算一个）：4 个以上的开放折线、曲线是数据线或轨迹，端点本来就悬空
  const start = (c, pt, T) => { (c.__P || (c.__P = [])).push({ pts: [pt], seg: 0, v: 1, closed: false, shape: false, T }); };
  const add = (c, pt, T, isSeg) => {
    let s = cur(c);
    if (!s) { start(c, pt, T); return; }
    if (s.closed) { start(c, s.pts[0], T); s = cur(c); }
    s.pts.push(pt); if (isSeg) s.seg++;
  };
  const vtx = c => { const s = cur(c); if (s) s.v++; };
  wrap('beginPath', function () { this.__P = []; });
  wrap('moveTo', function (x, y) { const T = this.getTransform(); start(this, tp(T, x, y), T); });
  wrap('lineTo', function (x, y) { const T = this.getTransform(); add(this, tp(T, x, y), T, true); vtx(this); });
  wrap('arcTo', function (x1, y1) { const T = this.getTransform(); add(this, tp(T, x1, y1), T, true); vtx(this); });
  const curve = (c, ctrl, T) => {
    if (!cur(c)) start(c, ctrl[0], T);
    const s = cur(c), p0 = s.closed ? s.pts[0] : s.pts[s.pts.length - 1], q = [p0, ...ctrl], n = q.length - 1;
    for (let k = 1; k <= 8; k++) {
      const u = k / 8; let pts = q.slice();
      for (let r = 0; r < n; r++) pts = pts.slice(0, -1).map((p, i) => [p[0] + (pts[i + 1][0] - p[0]) * u, p[1] + (pts[i + 1][1] - p[1]) * u]);
      add(c, pts[0], T, true);
    }
    vtx(c);
  };
  wrap('quadraticCurveTo', function (a, b, x, y) { const T = this.getTransform(); curve(this, [tp(T, a, b), tp(T, x, y)], T); });
  wrap('bezierCurveTo', function (a, b, c2, d, x, y) { const T = this.getTransform(); curve(this, [tp(T, a, b), tp(T, c2, d), tp(T, x, y)], T); });
  const sweep = (a0, a1, ccw) => {
    const TAU = Math.PI * 2; let d = ccw ? a0 - a1 : a1 - a0;
    if (d >= TAU - 1e-6) d = TAU; else { d %= TAU; if (d < 0) d += TAU; }
    return ccw ? -d : d;
  };
  const arcPts = (c, T, f, a0, d) => {
    const n = Math.max(2, Math.min(32, Math.ceil(Math.abs(d) / (Math.PI / 8))));
    const s0 = cur(c), first = tp(T, ...f(a0));
    if (!s0 || s0.closed) start(c, first, T); else add(c, first, T, Math.hypot(first[0] - s0.pts[s0.pts.length - 1][0], first[1] - s0.pts[s0.pts.length - 1][1]) > 0.5);
    for (let k = 1; k <= n; k++) add(c, tp(T, ...f(a0 + d * k / n)), T, false);
    const s = cur(c); if (Math.abs(d) >= Math.PI * 2 - 1e-6) s.shape = true;
  };
  wrap('arc', function (x, y, r, a0, a1, ccw) { const T = this.getTransform(); arcPts(this, T, a => [x + r * Math.cos(a), y + r * Math.sin(a)], a0, sweep(a0, a1, ccw)); });
  wrap('ellipse', function (x, y, rx, ry, rot, a0, a1, ccw) {
    const T = this.getTransform(), cr = Math.cos(rot), sr = Math.sin(rot);
    arcPts(this, T, a => { const u = rx * Math.cos(a), v = ry * Math.sin(a); return [x + u * cr - v * sr, y + u * sr + v * cr]; }, a0, sweep(a0, a1, ccw));
  });
  const rectSub = (c, x, y, w, h) => { const T = c.getTransform(); start(c, tp(T, x, y), T); const s = cur(c); s.pts.push(tp(T, x + w, y), tp(T, x + w, y + h), tp(T, x, y + h)); s.shape = true; s.closed = true; };
  wrap('rect', function (x, y, w, h) { rectSub(this, x, y, w, h); });
  wrap('roundRect', function (x, y, w, h) { rectSub(this, x, y, w, h); });
  wrap('closePath', function () { const s = cur(this); if (s) s.closed = true; });
  const bbox = pts => { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const [x, y] of pts) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); } return [x0, y0, x1, y1]; };
  const shape = (c, b, kind, a, id) => { if (window.__SHAPES.length < MAXN) window.__SHAPES.push({ b, kind, a, seq: window.__SEQ, id, shot: shotNow(), role: c.__role || null }); };
  wrap('stroke', function (p) {
    if (p instanceof Path2D) return;
    const seq = window.__SEQ++, a = this.globalAlpha * alphaOf(this.strokeStyle); let src;
    (this.__P || []).forEach((s, i) => {
      const id = seq * 100 + i, b = bbox(s.pts), f = s.pts[0], l = s.pts[s.pts.length - 1];
      shape(this, b, 'stroke', a, id);
      const closed = s.closed || s.shape || (s.pts.length > 2 && Math.hypot(f[0] - l[0], f[1] - l[1]) < 1.5);
      if (!closed && s.seg > 0 && window.__LINES.length < MAXN) {
        const T = s.T, step = Math.max(1, Math.ceil(s.pts.length / 64)), pts = s.pts.filter((_, k) => k % step === 0 || k === s.pts.length - 1);
        if (src === undefined) src = srcOf(new Error().stack);
        window.__LINES.push({ pts, v: s.v, lw: this.lineWidth * Math.sqrt(Math.abs(T.a * T.d - T.b * T.c)), a, seq, id, shot: shotNow(), dash: this.getLineDash().length > 0, m: camOf(T), src });
      }
    });
  });
  wrap('fill', function (p) {
    if (p instanceof Path2D) return;
    const seq = window.__SEQ++, a = this.globalAlpha * alphaOf(this.fillStyle);
    (this.__P || []).forEach((s, i) => shape(this, bbox(s.pts), 'fill', a, seq * 100 + i));
  });
  const rect4 = (c, x, y, w, h) => { const T = c.getTransform(); return bbox([tp(T, x, y), tp(T, x + w, y), tp(T, x, y + h), tp(T, x + w, y + h)]); };
  wrap('fillRect', function (x, y, w, h) { const seq = window.__SEQ++; shape(this, rect4(this, x, y, w, h), 'fill', this.globalAlpha * alphaOf(this.fillStyle), seq * 100); });
  wrap('strokeRect', function (x, y, w, h) { const seq = window.__SEQ++; shape(this, rect4(this, x, y, w, h), 'stroke', this.globalAlpha * alphaOf(this.strokeStyle), seq * 100); });
  wrap('drawImage', function (img, ...r) {
    const seq = window.__SEQ++, iw = img.videoWidth || img.naturalWidth || img.width, ih = img.videoHeight || img.naturalHeight || img.height;
    const d = r.length >= 8 ? r.slice(4, 8) : r.length >= 4 ? r.slice(0, 4) : [r[0], r[1], iw, ih];
    shape(this, rect4(this, ...d), 'image', this.globalAlpha, seq * 100);
  });
})();
"""
# 页面就绪后再包装镜头函数（core.js 加载后才有）：记下这一刻最近一次 cam / screen 的参数，报告里写「镜头变换」
CAM_JS = r"""(() => {
  const wrap = (n, f) => { if (typeof window[n] !== 'function' || window[n].__wrapped) return; const o = window[n]; window[n] = function (...a) { try { window.__CAMNOW = f(a); } catch (e) {} return o.apply(this, a); }; window[n].__wrapped = true; };
  wrap('cam', a => ({ fn: 'cam', cx: a[1] ?? W / 2, cy: a[2] ?? H / 2, z: a[3] ?? 1 }));
  wrap('camSet', a => ({ fn: 'camSet', cx: a[1] ?? W / 2, cy: a[2] ?? H / 2, z: a[3] ?? 1 }));
  wrap('screen', a => ({ fn: 'screen' }));
  // 引线和文字块登记时记下镜头文件的行号（callout 往 __LINKS 推、textBlock 放不下时往 __TEXTFIT 推）
  const mark = (n, list) => { if (typeof window[n] !== 'function' || window[n].__marked) return; const o = window[n];
    window[n] = function (...a) { const L = window[list] || [], n0 = L.length, r = o.apply(this, a), L2 = window[list] || [];
      const src = window.__SRCOF(new Error().stack); (window.__MARKSRC || (window.__MARKSRC = {}))[n + ':' + a[1]] = src;   // 目标不存在时没有登记，按名字找行号
      if (L2.length > n0) for (let i = n0; i < L2.length; i++) if (L2[i] && !L2[i].src) L2[i].src = src;
      return r; }; window[n].__marked = true; };
  mark('callout', '__LINKS'); mark('textBlock', '__TEXTFIT');
})()"""
GRAB_JS = ('({txt: window.__TXT, lines: window.__LINES, shapes: window.__SHAPES, anchors: window.__ANCHORS || null, links: window.__LINKS || null, fits: window.__TEXTFIT || [], acts: window.__ACTS || [], marks: window.__MARKSRC || {},'
           ' subs: window.__SUBS ? JSON.parse(JSON.stringify(window.__SUBS)) : null})')
CLEAR_JS = 'window.__TXT.length = 0; window.__LINES.length = 0; window.__SHAPES.length = 0; window.__SEQ = 0; window.__CAMNOW = null'

ARGV = sys.argv[1:]
FMTS = pop_format(ARGV)
CFG = project(); TL = timeline()
NAME = ARGV[0] if ARGV else None
SAFE = 0.05   # 和 core.js 的 SAFE 一致
OVL = 0.03    # 两行字外框相交超过小框面积 3% 就算压住
LATER = 0.15  # 运动中的短暂重叠、正在生长的线不报：这么多秒后再看一次
TOUCH = 4     # 线头离目标 4 像素以内算碰到
HAS_TEXT = re.compile(r'[\w\u3040-\u30ff\u4e00-\u9fff]')
# 过程标注词：对需求的回应（时长、片型）、制作过程的标注（示意、版本）、没换掉的占位字（YOUR NAME、Lorem ipsum、公司名）。大小写不敏感
PROCESS_WORDS = re.compile(r'\b\d+\s*(?:SECONDS?|SECS?)\b|\bEXPLAIN(?:ED|ER)\b|教学示意|示意|\bDEMO\b|(?<![\w.])v\d+(?:\.\d+)*\b|版本|占位|\bPLACEHOLDER\b', re.I)
PLACEHOLDER = re.compile(r'\bYOUR[\s_-]*(?:NAME|LOGO|TEXT|TITLE|COMPANY|BRAND|PRODUCT|TAGLINE|HEADLINE|EMAIL|WEBSITE|URL)\b|\b(?:LOGO|TEXT|NAME|TITLE|IMAGE)\s+HERE\b'
                         r'|\bLOREM\s+IPSUM\b|\bDOLOR\s+SIT\s+AMET\b|\bTB[DA]\b|\bX{3,}\b|\bCOMPANY\s+NAME\b|\bBRAND\s+NAME\b|\bPRODUCT\s+NAME\b|\bSAMPLE\s+TEXT\b'
                         r'|(?:公司|品牌|产品|项目|客户)名(?:称)?(?![\u4e00-\u9fff])|你的名字|您的名字|此处(?:填写|输入|替换|放)|某某', re.I)
VIEW = ROOT / 'frames' / '_view'; VIEW.mkdir(parents=True, exist_ok=True)
GENRE = CFG.get('genre') or ('explainer' if TL.get('mode') == 'voice' else 'promo')
# 主体大小：两个量都低才报 ⚠️「主体偏小、留白多」（按镜头取各取样点的中位数）
#   内容覆盖：画面分成约 144 格（16×9；竖版 9×16；方形 12×12）。每个像素按和背景的色差折成「墨量」(色差 - 12) / 96（0–1），
#     一格的平均墨量 ≥ CELL_INK 算「有内容」，有内容的格子占比就是覆盖。按墨量算，细线、暗淡的框、小字只占很少，实心的物件、大字才撑得起一格
#   最大字高：这一刻观众要读的字（非 deco、透明度 ≥ 0.6、不是常驻的页眉角标）里最大的大写字母高度，除以画面短边
#   讲解片观众有时间读，允许更多留白；宣传片在信息流里一眼要看清，主体要更大。
#   阈值按成片校准：字小、元素小、大片留白的讲解片镜头会被报出，主体饱满、字够大的镜头不报。两个量都低才报，单看一个会误报图表和大字镜头。
CELL_INK = 0.10
SUBJECT_MIN = {'explainer': (0.30, 0.040), 'promo': (0.35, 0.050)}     # (内容覆盖, 最大字高 / 短边)
RED, MAG, ORG = (230, 40, 40), (230, 40, 230), (255, 150, 0)


def sample_times():
    """每个镜头的 0.3/0.6/0.9 处，节拍片再加每一拍。"""
    ts = set()
    for s in TL['scenes'].values():
        for f in (0.3, 0.6, 0.9): ts.add(round(s['t0'] + f * s['dur'], 3))
    beat, off = TL.get('beat'), TL.get('offset', 0)
    if TL.get('mode') in ('beats', 'manual') and beat:
        k = 0
        while off + k * beat < TL['total'] - 1e-3: ts.add(round(off + k * beat, 3)); k += 1
    beat = beat or 0
    gaps = [(off + g['from'] * beat - 1e-3, off + g['to'] * beat - 1e-3) for g in (CFG.get('music') or {}).get('sections', []) if g.get('type') == 'gap' and beat]
    return sorted(t for t in ts if 0 <= t < TL['total'] and not any(a <= t < z for a, z in gaps))   # 空拍本来就该空


def scene_of(t):
    ss = sorted(TL['scenes'].values(), key=lambda s: s['t0'])
    cur = ss[0]['id']
    for s in ss:
        if s['t0'] <= t + 1e-6: cur = s['id']
    return cur


def later_time(t):
    """复查的时刻：同一镜头里往后 LATER 秒，到镜头末尾就往前"""
    s = TL['scenes'][scene_of(t)]
    return t + LATER if t + LATER < s['t1'] - 1e-3 else max(s['t0'], t - LATER)


# ---------------------------------------------------------------- 文字
def dedupe(items):
    """同一段字在同一位置的重复绘制（描边 + 填充、投影、多遍描边）合并成一个外框：字相同、字体相同、位置差不到 0.2 个字号。"""
    out = []
    for it in items:
        tol = 0.2 * max(it['fs'], 1)
        for k in range(len(out) - 1, max(-1, len(out) - 400), -1):
            o = out[k]
            if o['s'] == it['s'] and o['font'] == it['font'] and abs(o['x0'] - it['x0']) <= tol and abs(o['ay'] - it['ay']) <= tol:
                for a, f in (('x0', min), ('y0', min), ('x1', max), ('y1', max), ('a', max)): o[a] = f(o[a], it[a])
                o['raw'] = o['raw'] or it['raw']; o['deco'] = o.get('deco') or it.get('deco'); o['kind'] = o['kind'] if o['kind'] == it['kind'] else 'fill+stroke'
                break
        else:
            out.append(dict(it))
    return out


def merge_lines(items):
    """相邻的绘制调用（同字体、基线差 ≤ 2 像素、水平间距小于 0.6 个字高）合并成一行。英文字母之间隔开 0.15 个字号以上的补一个空格。"""
    lines = []
    for it in dedupe(items):
        if lines:
            g = lines[-1]; last = g['_last']
            gap = it['x0'] - last['x1']
            if it['font'] == last['font'] and abs(it['ay'] - last['ay']) <= 2 and -0.3 * it['fs'] <= gap < 0.6 * it['fs']:
                sp = ' ' if gap > 0.15 * it['fs'] and re.search(r'[A-Za-z0-9.,!?]$', g['s']) and re.match(r'[A-Za-z0-9]', it['s']) else ''   # 逐字画的英文：字间的空格没有单独画
                g['s'] += sp + it['s']; g['x0'] = min(g['x0'], it['x0']); g['x1'] = max(g['x1'], it['x1'])
                g['y0'] = min(g['y0'], it['y0']); g['y1'] = max(g['y1'], it['y1'])
                g['a'] = min(g['a'], it['a']); g['cap'] = max(g['cap'], it['cap']); g['deco'] = g.get('deco') or it.get('deco'); g['_last'] = it; continue
        lines.append(dict(it, _last=it))
    return lines


def overlaps(vis, shapes=()):
    """外框明显相交的两行字。先画的那行被之后画的不透明填充（透明度 ≥ 0.8，画在两行之间）盖住相交处的，不算：它在卡片底下看不见。"""
    cover = [s for s in shapes if s['kind'] in ('fill', 'image') and s['a'] >= 0.8]
    pairs = []
    for i in range(len(vis)):
        for j in range(i + 1, len(vis)):
            p, q = vis[i], vis[j]
            if p['s'].strip() == q['s'].strip(): continue
            iw = min(p['x1'], q['x1']) - max(p['x0'], q['x0']); ih = min(p['y1'], q['y1']) - max(p['y0'], q['y0'])
            if iw <= 0 or ih <= 0: continue
            small_area = min((p['x1'] - p['x0']) * (p['y1'] - p['y0']), (q['x1'] - q['x0']) * (q['y1'] - q['y0']))
            if not (small_area > 0 and iw * ih / small_area > OVL): continue
            lo, hi = sorted((p.get('seq', 0), q.get('seq', 0)))
            mx, my = (max(p['x0'], q['x0']) + min(p['x1'], q['x1'])) / 2, (max(p['y0'], q['y0']) + min(p['y1'], q['y1'])) / 2
            if any(lo < s['seq'] <= hi and s['b'][0] <= mx <= s['b'][2] and s['b'][1] <= my <= s['b'][3] for s in cover): continue
            pairs.append((p, q))
    return pairs


# ---------------------------------------------------------------- 线
def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def box_d(p, B):
    """点到一组外框的距离（在框里为 0）。B: N×4"""
    if not len(B): return np.zeros(0)
    dx = np.maximum(np.maximum(B[:, 0] - p[0], 0), p[0] - B[:, 2]); dy = np.maximum(np.maximum(B[:, 1] - p[1], 0), p[1] - B[:, 3])
    return np.hypot(dx, dy)


def seg_d(p, S):
    """点到一组线段的距离。S: M×4 (x0, y0, x1, y1)"""
    if not len(S): return np.zeros(0)
    a, b = S[:, :2], S[:, 2:]; ab = b - a; L2 = (ab ** 2).sum(1); L2[L2 == 0] = 1e-9
    u = np.clip(((p - a) * ab).sum(1) / L2, 0, 1)
    return np.hypot(*(a + ab * u[:, None] - p).T)


def segs_of(pts):
    return np.array([[*a, *b] for a, b in zip(pts, pts[1:])], float).reshape(-1, 4)


def crosses(A, B):
    """两组线段有没有相交（A: n×4, B: m×4）"""
    if not len(A) or not len(B): return False
    p, r = A[:, None, :2], (A[:, 2:] - A[:, :2])[:, None]; q, s = B[None, :, :2], (B[:, 2:] - B[:, :2])[None]
    cr = lambda u, v: u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]
    den = cr(r, s); qp = q - p
    with np.errstate(divide='ignore', invalid='ignore'):
        t = cr(qp, s) / den; u = cr(qp, r) / den
    return bool(np.any((np.abs(den) > 1e-9) & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)))


def clip_seg(x0, y0, x1, y1, B):
    """线段在矩形 B 里的那一截（Liang–Barsky），没有返回 None"""
    dx, dy = x1 - x0, y1 - y0; u0, u1 = 0.0, 1.0
    for p, q in ((-dx, x0 - B[0]), (dx, B[2] - x0), (-dy, y0 - B[1]), (dy, B[3] - y0)):
        if abs(p) < 1e-12:
            if q < 0: return None
        else:
            r = q / p
            if p < 0: u0 = max(u0, r)
            else: u1 = min(u1, r)
    if u0 > u1 or u1 - u0 < 1e-6: return None
    return (x0 + dx * u0, y0 + dy * u0, x0 + dx * u1, y0 + dy * u1)


def line_issues(fd, W, H, texts):
    """返回 (悬空的线 [line], 穿过文字 [(line, text)])"""
    lines = [l for l in fd['lines'] if l['a'] >= 0.3 and len(l['pts']) >= 2]
    for l in lines:
        l['L'] = plen(l['pts']); l['S'] = segs_of(l['pts'])
        xs = [p[0] for p in l['pts']]; ys = [p[1] for p in l['pts']]; l['bb'] = (min(xs), min(ys), max(xs), max(ys))
    lines = [l for l in lines if l['bb'][2] > 0 and l['bb'][0] < W and l['bb'][3] > 0 and l['bb'][1] < H]
    full = 0.85 * W * H                                           # 铺满画面的底色、纹理不算目标
    shapes = [s for s in fd['shapes'] if s['a'] >= 0.1 and (s['b'][2] - s['b'][0]) * (s['b'][3] - s['b'][1]) < full and s['b'][2] >= s['b'][0]]
    tb = np.array([[g['x0'], g['y0'], g['x1'], g['y1']] for g in texts], float).reshape(-1, 4)
    ab = np.array([[r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']] for r in (fd.get('anchors') or {}).values()], float).reshape(-1, 4)
    edge = lambda p: p[0] < TOUCH or p[0] > W - TOUCH or p[1] < TOUCH or p[1] > H - TOUCH
    dangling, crossing = [], []
    for l in lines:
        if l['L'] < 12: continue                                  # 小记号、刻度
        bw, bh = l['bb'][2] - l['bb'][0], l['bb'][3] - l['bb'][1]
        if max(bw, bh) < 24: continue                              # 勾、叉这类小符号
        p0, p1 = l['pts'][0], l['pts'][-1]
        # 水平或竖直的直线是分隔线、横条、两个框之间的箭头，本来就不连着东西；查悬空的是斜线、折线、曲线这类引线
        axis = min(bw, bh) <= max(2.0, 0.05 * max(bw, bh))
        tol = TOUCH + l['lw'] / 2
        others = [o for o in lines if o is not l and o['a'] >= 0.1]
        OS = np.concatenate([o['S'] for o in others]) if others else np.zeros((0, 4))
        def own_deco(s, p):                                        # 紧跟着画的箭头、端点圆点是线自己的一部分，不算目标
            b = s['b']; return 0 < s['seq'] - l['seq'] <= 3 and max(b[2] - b[0], b[3] - b[1]) <= max(6 * l['lw'], 28) and box_d(p, np.array([b]))[0] <= tol
        def touched(p):
            if edge(p): return True                                # 伸出画面
            pp = np.array(p, float)
            if len(tb) and box_d(pp, tb).min() <= tol: return True
            if len(ab) and box_d(pp, ab).min() <= tol: return True
            sb = [s for s in shapes if s['id'] != l['id'] and not own_deco(s, p)]
            if sb and box_d(pp, np.array([s['b'] for s in sb], float)).min() <= tol: return True
            if len(OS) and seg_d(pp, OS).min() <= tol: return True
            return False
        data = l.get('v', 2) >= 4                                  # 4 个以上顶点的开放折线、曲线：数据线、轨迹，端点本来就悬空
        if not axis and not data and not touched(p0) and not touched(p1):
            under = abs(p1[1] - p0[1]) <= 0.12 * max(1, abs(p1[0] - p0[0])) and any(   # 下划线、上划线、删除线
                min(g['x1'], l['bb'][2]) - max(g['x0'], l['bb'][0]) >= 0.5 * bw and g['y0'] - 0.8 * g['cap'] <= p0[1] <= g['y1'] + 0.8 * g['cap'] for g in texts)
            if not under and not crosses(l['S'], OS): dangling.append(l)
        if l['a'] >= 0.45 and l['lw'] >= 1.5 and not edge(p0) and not edge(p1):   # 伸出画面的线是地平线、背景线条，不算
            for g in texts:
                if g['a'] < 0.5 or not HAS_TEXT.search(g['s']): continue
                h = g['y1'] - g['y0']; core = (g['x0'] + 0.05 * h, g['y0'] + 0.2 * h, g['x1'] - 0.05 * h, g['y1'] - 0.2 * h)
                if core[2] <= core[0] or core[3] <= core[1]: continue
                grown = (g['x0'] - tol, g['y0'] - tol, g['x1'] + tol, g['y1'] + tol)
                if any(grown[0] <= p[0] <= grown[2] and grown[1] <= p[1] <= grown[3] for p in (p0, p1)): continue   # 这段字是线头的标签
                hit = None
                for x0, y0, x1, y1 in l['S']:
                    c = clip_seg(x0, y0, x1, y1, core)
                    if c is None: continue
                    mx, my = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
                    masked = any(s['kind'] in ('fill', 'image') and s['a'] >= 0.8 and s['seq'] > l['seq'] and s['b'][0] <= mx <= s['b'][2] and s['b'][1] <= my <= s['b'][3] for s in shapes)
                    if not masked: hit = c; break
                if hit: crossing.append((l, g))
    return dangling, crossing


def link_issues(fd, errs):
    """引线终点不在目标锚点里（4 像素以内），或目标这一帧不存在"""
    out = []
    A = fd.get('anchors') or {}
    for k in fd.get('links') or []:
        if (k.get('p') if k.get('p') is not None else 1) < 1 - 1e-6: continue   # 还在生长的引线，等长完再查
        r = A.get(k.get('to'))
        if not r: out.append((k, None)); continue
        x, y = k['end']
        d = max(r['x'] - x, 0, x - r['x'] - r['w']), max(r['y'] - y, 0, y - r['y'] - r['h'])
        if math.hypot(*d) > TOUCH: out.append((k, r))
    for e in errs:
        m = re.search(r'callout：这一帧没有锚点「([^」]+)」', e)
        if m: out.append(({'to': m.group(1), 'missing': True}, None))
    return out


# ---------------------------------------------------------------- 主体大小：内容覆盖
def _hex(c):
    c = (c or '').strip().lstrip('#')
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) if len(c) >= 6 else None


THEME_BG = _hex(((CFG.get('theme') or {}).get('colors') or {}).get('bg'))
_VIG = {}


def grid_shape(W, H):
    """约 144 格，按画幅比例：16×9、9×16、12×12"""
    rows = max(3, round(math.sqrt(144 * H / W))); return max(3, round(144 / rows)), rows


def _vig(w, h, W, H):
    """后期暗角的透明度（和 core.js 的 postFX 同一个径向渐变），缩到 w×h。算背景时先除掉它，浅色底的四角才不会被当成内容。"""
    v = dict({'vignette': 0.3}, **(CFG.get('post') or {})).get('vignette') or 0
    k = (w, h, W, H, v)
    if k not in _VIG:
        ys, xs = np.mgrid[0:h, 0:w]; r = np.hypot((xs + 0.5) * W / w - W / 2, (ys + 0.5) * H / h - H / 2)
        r0, r1 = min(W, H) * 0.45, math.hypot(W, H) * 0.55
        _VIG[k] = (v * np.clip((r - r0) / (r1 - r0), 0, 1)).astype(np.float32)
    return _VIG[k]


def content_stats(im, W, H):
    """内容覆盖：返回 (有内容的格子占比, 格子串 '0110…'（行优先）, 色差明显的像素占比（< 0.0015 算空画面，口径同旧版主体检测）)。im 是缩小后的 PIL 图。
    背景色取 theme.colors.bg（画面里这个颜色少于 15% 时改用画面里最多的颜色，例如整屏铺色的镜头），先除掉后期暗角。"""
    a = np.asarray(im.convert('RGB'), np.float32); h, w = a.shape[:2]
    a = (a / (1 - _vig(w, h, W, H))[..., None]).clip(0, 255)
    bg = THEME_BG
    if bg is None or (np.abs(a - bg).max(-1) <= 24).mean() < 0.15:
        q = (a // 16).astype(np.int32); k = q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]
        bg = a[k == np.bincount(k.ravel()).argmax()].mean(0)
    d = np.abs(a - bg).max(-1); ink = np.clip((d - 12) / 96, 0, 1)
    cols, rows = grid_shape(W, H)
    ys = np.linspace(0, h, rows + 1).round().astype(int); xs = np.linspace(0, w, cols + 1).round().astype(int)
    cells = ''.join('1' if ink[ys[r]:ys[r + 1], xs[c]:xs[c + 1]].mean() >= CELL_INK else '0' for r in range(rows) for c in range(cols))
    from scipy.ndimage import uniform_filter
    return cells.count('1') / len(cells), cells, float((uniform_filter(d, 2) > 22).mean())


def content_box(cells, cols, rows):
    """有内容的格子的外接矩形，按画面比例（0–1）：(x0, y0, x1, y1)；没有内容返回 None"""
    on = [(i % cols, i // cols) for i, c in enumerate(cells) if c == '1']
    if not on: return None
    xs, ys = [c for c, _ in on], [r for _, r in on]
    return min(xs) / cols, min(ys) / rows, (max(xs) + 1) / cols, (max(ys) + 1) / rows


def enlarge_hint(cells, cols, rows):
    """主体偏小时能照着改的量：内容外框占安全区多少、等比放大几倍能占满、最大的空白在哪一侧。返回 (说明, 放大倍数)。
    外框按格子量，比实际内容略大，所以倍数是保守值。"""
    b = content_box(cells, cols, rows)
    if b is None: return '画面上没有成块的内容', None
    s0, s1, sw = SAFE, 1 - SAFE, 1 - 2 * SAFE
    bw, bh = b[2] - b[0], b[3] - b[1]
    share = min(1.0, bw * bh / (sw * sw)); k = min(sw / bw, sw / bh)
    gaps = {'左': (b[0] - s0) / sw, '右': (s1 - b[2]) / sw, '上': (b[1] - s0) / sw, '下': (s1 - b[3]) / sw}
    side = max(gaps, key=gaps.get); g = gaps[side]
    half = {'左': '左半幅', '右': '右半幅', '上': '上半幅', '下': '下半幅'}[side]
    where = (f'{half}空' if g >= 0.45 else f'{side}侧空着（占安全区{"宽" if side in "左右" else "高"}的 {g * 100:.0f}%）') if g >= 0.15 else ''
    if not where:                                                  # 外框已经铺开：看哪一半内容少
        on = [i for i, c in enumerate(cells) if c == '1']
        cnt = {'左半幅': sum(1 for i in on if i % cols < cols / 2), '右半幅': sum(1 for i in on if i % cols >= cols / 2),
               '上半幅': sum(1 for i in on if i // cols < rows / 2), '下半幅': sum(1 for i in on if i // cols >= rows / 2)}
        pairs = (('左半幅', '右半幅'), ('上半幅', '下半幅'))
        lo, hi = max(pairs, key=lambda p: abs(cnt[p[0]] - cnt[p[1]]))
        if cnt[lo] > cnt[hi]: lo, hi = hi, lo
        if cnt[hi] >= 2 * max(1, cnt[lo]): where = f'{lo}内容少（有内容的格子 {cnt[lo]} 个，{hi} {cnt[hi]} 个）'
    kw, kh = sw / bw, sw / bh
    if k >= 1.15:
        msg = f'内容外框占安全区 {share * 100:.0f}%，等比放大到约 {k:.1f} 倍可占满' + (f'；{where}' if where else '')
    elif max(kw, kh) >= 1.3:                                       # 一个方向已经铺满，另一个方向空着：不必等比，沿空的方向放大
        full, room, kk = ('宽', '高', kh) if kw < kh else ('高', '宽', kw)
        msg = (f'内容外框占安全区 {share * 100:.0f}%：{full}已铺满，{room}只用了 {100 / kk:.0f}%，沿{"纵" if room == "高" else "横"}向放大到约 {kk:.1f} 倍可占满'
               f'（把物件、窗口加{room}，或把分区{"上下" if room == "高" else "左右"}用满）' + (f'；{where}' if where else ''))
        k = kk
    else:
        msg = (f'内容外框已占安全区 {share * 100:.0f}%，再放大就碰边：主体小是因为内容稀（细线、小字、元素之间留空多），'
               f'把物件本身画大、线加粗，或把零散的小元素合并成大块' + (f'；{where}' if where else ''))
    return msg, round(k, 2)


def read_lines(lines, W, H):
    """这一刻观众要读的字（非 deco、透明度 ≥ 0.6、在画面里）：[[x0, y0, cap, 文字]]"""
    return [[round(g['x0']), round(g['y0']), round(g['cap'], 1), g['s'].strip()[:16]] for g in lines
            if g['a'] >= 0.6 and not g.get('deco') and g['x1'] > 0 and g['x0'] < W and g['y1'] > 0 and g['y0'] < H]


def chrome_keys(subj, W, H):
    """常驻字：同一个位置（按画面 2% 取整）、同样字高的字出现在 3 个以上镜头、四成以上的取样点里，例如页眉的年份、章节标签。
    它们是导航，不是这一刻要读的内容，不算进最大字高。"""
    seen = {}
    for s in subj:
        for x0, y0, cap, _ in s['lines']:
            e = seen.setdefault((round(x0 / W * 50), round(y0 / H * 50), round(cap / 4)), [set(), set()]); e[0].add(s['t']); e[1].add(s['shot'])
    n = len(subj)
    return {k for k, (ts, ss) in seen.items() if len(ss) >= 3 and len(ts) >= max(4, 0.4 * n)}


def finish_subject(subj, W, H):
    """取样全部做完后：去掉常驻字，算每个取样点的最大字高（相对短边）"""
    ch = chrome_keys(subj, W, H)
    for s in subj:
        caps = [cap for x0, y0, cap, _ in s['lines'] if (round(x0 / W * 50), round(y0 / H * 50), round(cap / 4)) not in ch]
        s['text'] = round(max(caps) / min(W, H), 4) if caps else 0.0
    return sorted({l[3] for s in subj for l in s['lines'] if (round(l[0] / W * 50), round(l[1] / H * 50), round(l[2] / 4)) in ch})


# ---------------------------------------------------------------- 定位说明
def where(t, box, m, shot):
    """取样时刻、屏幕外框、镜头、镜头变换"""
    d = {'t': round(t, 3), 'shot': shot or scene_of(t), 'box': [round(v) for v in box]}
    s = f"{d['shot']} t={t:.2f}s 屏幕 ({d['box'][0]}, {d['box'][1]})–({d['box'][2]}, {d['box'][3]})"
    if m:
        c = m.get('cam')
        if c and c.get('fn') != 'screen' and c.get('cx') is not None:
            d['cam'] = {k: round(c[k], 3) for k in ('cx', 'cy', 'z')}; s += f"　镜头 {c['fn']}(中心 {c['cx']:.0f}, {c['cy']:.0f}，缩放 ×{c['z']:.2f})"
        elif c: d['cam'] = {'fn': 'screen'}; s += '　镜头 screen（无推拉）'
        d['matrix'] = {'scale': round(m['s'], 3), 'tx': round(m['e'], 1), 'ty': round(m['f'], 1)}
        s += f"　变换 缩放 ×{m['s']:.2f} 位移 ({m['e']:.0f}, {m['f']:.0f})"
    d['text'] = s
    return d


def overflow_msg(g, W, H):
    """出框说明：哪一侧、超出多少，或离边缘多近；镜头推近时附上缩放"""
    m = SAFE / 2; out = []
    for side, d, lim in (('左侧', g['x0'], m * W), ('右侧', W - g['x1'], m * W), ('上方', g['y0'], m * H), ('下方', H - g['y1'], m * H)):
        if d < 0: out.append(f'{side}超出画面 {-d:.0f}px')
        elif d < lim: out.append(f'{side}离边缘 {d:.0f}px，至少要 {lim:.0f}px')
    s = '，'.join(out)
    sc = (g.get('m') or {}).get('s')
    if sc and abs(sc - 1) > 0.02: s += f'；这一刻镜头缩放 ×{sc:.2f}'
    return s


def sub_hits(fd, texts, W, H):
    """字幕开着时，压进字幕带的字和锚点目标。返回 (字幕带 [x0, y0, x1, y1], 字幕语言, [('字' 或 '锚点', 文字或锚点名, 外框)])；没开字幕或没有压进去的返回 None"""
    S = fd.get('subs') or {}; b = S.get('box')
    if not S.get('on') or not b: return None
    B = (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])
    inter = lambda r: max(0, min(r[2], B[2]) - max(r[0], B[0])) * max(0, min(r[3], B[3]) - max(r[1], B[1]))
    area = lambda r: max(1e-6, (r[2] - r[0]) * (r[3] - r[1]))
    hits = [('字', g['s'].strip(), (g['x0'], g['y0'], g['x1'], g['y1'])) for g in texts
            if g['a'] >= 0.5 and not g.get('deco') and inter((g['x0'], g['y0'], g['x1'], g['y1'])) >= 0.2 * area((g['x0'], g['y0'], g['x1'], g['y1']))]
    hits += [('锚点', k, r) for k, a in (fd.get('anchors') or {}).items()
             for r in [(a['x'], a['y'], a['x'] + a['w'], a['y'] + a['h'])] if inter(r) >= 0.3 * area(r)]
    return (B, S.get('langs'), hits) if hits else None


def grab(pg, t):
    pg.evaluate(CLEAR_JS); pg.evaluate(f'render({t})')
    return pg.evaluate(GRAB_JS)


def audit(pg, W, H, min_text, errs):
    """逐个取样时刻检查。返回 (问题 rows, 问题帧 {t: (缩略图, 框)}, 主体取样 [{t, shot, cov, cells, text, px}])"""
    rows, flagged, subj = [], {}, []
    global DECO, FITS, ACTS, RAW; DECO = {}; FITS = {}; ACTS = {}; RAW = {}   # 装饰字 (镜头, 文字, 原因) → [时刻, 最小字高]；放不下的文字块；画面事件；直接 fillText 的字
    TH = 480 if W >= H else 300
    for t in sample_times():
        n_err = len(errs)
        fd = grab(pg, t)
        small = Image.open(io.BytesIO(snap(pg, q=85, scale=TH / W))).convert('RGB'); sc = TH / W
        lines = [g for g in merge_lines(fd['txt']) if HAS_TEXT.search(g['s'])]
        main = [g for g in lines if g.get('role') != 'subtitle']          # 字幕的字只查字太小和出框
        cov, cells, px = content_stats(small, W, H)
        subj.append({'t': t, 'shot': scene_of(t), 'cov': round(cov, 3), 'cells': cells, 'lines': read_lines(main, W, H), 'px': round(px, 4)})
        for f in fd.get('fits') or []:
            k = (f.get('shot') or scene_of(t), str(f.get('text', '')))
            e = FITS.setdefault(k, dict(f, times=[t])); e['src'] = e.get('src') or f.get('src')    # 引擎不一定每帧清空 __TEXTFIT，只记第一次碰到的时刻
        for a in fd.get('acts') or []:
            ACTS.setdefault((a.get('name'), a.get('at'), a.get('shot')), a)
        boxes = []                                                   # (框, 颜色)
        def add(level, kind, msg, text, loc=None, box=None, col=RED, shot=None, src=None):
            rows.append((shot or (loc or {}).get('shot') or scene_of(t), t, level, kind, msg, text, loc, src, [round(v) for v in box] if box else None))
            if box: boxes.append((box[0] * sc, box[1] * sc, box[2] * sc, box[3] * sc, col))
        def gbox(g): return (g['x0'], g['y0'], g['x1'], g['y1'])
        for g in lines:
            vis = g['x1'] > 0 and g['x0'] < W and g['y1'] > 0 and g['y0'] < H
            if not vis: continue
            txt = g['s'].strip()[:24]; loc = where(t, gbox(g), g.get('m'), g.get('shot')); src = g.get('src')
            if g.get('deco'):
                k = (loc['shot'], txt, g['deco']); e = DECO.setdefault(k, [[], 1e9]); e[0].append(t); e[1] = min(e[1], g['cap'])
            elif g['a'] >= 0.6 and g['cap'] < min_text:
                add('❌', '字太小', f"字高 {g['cap']:.0f}px，下限 {min_text:.0f}px", txt, loc, gbox(g), src=src)
            m = SAFE / 2                                             # 安全区边距的一半：drift 推近后也保证留出的边
            if g['a'] >= 0.6 and not g.get('deco') and (g['x0'] < m * W or g['x1'] > (1 - m) * W or g['y0'] < m * H or g['y1'] > (1 - m) * H):
                add('❌', '文字出框', overflow_msg(g, W, H), txt, loc, gbox(g), src=src)
            if g.get('raw') and g['a'] >= 0.3 and not g.get('deco'):
                RAW.setdefault(txt, (loc['shot'], t, src))                # 整片合并成一条提示（report 里）
            if g['a'] >= 0.3 and g.get('role') != 'subtitle':
                ph = PLACEHOLDER.search(g['s']); pw = PROCESS_WORDS.search(g['s'])
                if ph: add('⚠️', '占位字', f"「{ph.group(0)}」没换掉：换成真实内容或删掉", txt, loc, gbox(g), src=src)
                elif pw: add('ℹ️', '过程标注词', f"「{pw.group(0)}」：时长、片型、示意、版本这类词观众多半用不上", txt, loc, gbox(g), src=src)
        vis = [g for g in main if g['a'] > 0.3]                     # 半透明（正在淡入淡出）的字也算：换句时两段叠在一起就是这样
        pairs = overlaps(vis, fd['shapes'])
        dang, cross = line_issues(fd, W, H, [g for g in main if g['x1'] > 0 and g['x0'] < W])
        links = link_issues(fd, errs[n_err:])
        band = sub_hits(fd, main, W, H)
        if pairs or dang or cross or band:                           # 运动中的短暂重叠、正在生长的线、飞过字幕带的内容不报：过一会儿再看一次
            fd2 = grab(pg, later_time(t))
            l2 = [g for g in merge_lines(fd2['txt']) if HAS_TEXT.search(g['s']) and g.get('role') != 'subtitle']
            if band and not sub_hits(fd2, l2, W, H): band = None
            still = {frozenset((p['s'].strip()[:12], q['s'].strip()[:12])) for p, q in overlaps([g for g in l2 if g['a'] > 0.3], fd2['shapes'])}
            pairs = [(p, q) for p, q in pairs if frozenset((p['s'].strip()[:12], q['s'].strip()[:12])) in still]
            d2, c2 = line_issues(fd2, W, H, [g for g in l2 if g['x1'] > 0 and g['x0'] < W])
            near = lambda a, b: all(math.hypot(u[0] - v[0], u[1] - v[1]) <= 8 for u, v in zip((a['pts'][0], a['pts'][-1]), (b['pts'][0], b['pts'][-1])))
            dang = [l for l in dang if any(near(l, k) for k in d2)]
            ctext = {g['s'].strip() for _, g in c2}
            cross = [(l, g) for l, g in cross if g['s'].strip() in ctext]
            grab(pg, t)                                              # 回到这一刻（下面没有再读画面，只为状态一致）
        if pairs:                                                    # 一个时刻只报一行，逐字动画的字符碰撞很多时不刷屏
            strong = [(p, q) for p, q in pairs if min(p['a'], q['a']) >= 0.5]   # 两行都清楚：❌；有一行半透明（0.3–0.5）：⚠️，不拦渲染
            p, q = (strong or pairs)[0]
            bx = (min(p['x0'], q['x0']), min(p['y0'], q['y0']), max(p['x1'], q['x1']), max(p['y1'], q['y1']))
            add('❌' if strong else '⚠️', '文字互相压住', f'和「{q["s"].strip()[:12]}」的外框相交' + ('' if strong else f'（有一行半透明，可见度 {min(p["a"], q["a"]):.2f}，仍看得见）') +
                (f'（这一刻共 {len(pairs)} 对）' if len(pairs) > 1 else ''),
                p['s'].strip()[:24], where(t, bx, p.get('m'), p.get('shot')), bx, src=p.get('src') or q.get('src'))
            for a, b in pairs[:6]: boxes.append((min(a['x0'], b['x0']) * sc, min(a['y0'], b['y0']) * sc, max(a['x1'], b['x1']) * sc, max(a['y1'], b['y1']) * sc, RED))
        if band:
            B, ts_, hits = band
            bx = (min(h[0] for _, _, h in hits), max(B[1], min(h[1] for _, _, h in hits)), max(h[2] for _, _, h in hits), min(B[3], max(h[3] for _, _, h in hits)))
            words = [x for k, x, _ in hits if k == '字'][:3]; anchs = [x for k, x, _ in hits if k == '锚点'][:3]
            what = '、'.join(x for x in ((f"字{'、'.join('「' + w[:10] + '」' for w in words)}" if words else ''),
                                       (f"anchor 登记的目标{'、'.join('「' + a + '」' for a in anchs)}" if anchs else '')) if x)
            add('⚠️', '画面内容进了字幕带', f"字幕带 y {B[1]:.0f}–{B[3]:.0f}px 里有{what}：放进 safeBox() 以内（字幕开着时它已让出字幕带）；推近镜头让目标留在分区里，或把这一块上移",
                '', where(t, bx, None, None), bx, ORG)
        for l in dang:
            p0, p1 = l['pts'][0], l['pts'][-1]
            add('ℹ️', '线头悬空', f"线 ({p0[0]:.0f}, {p0[1]:.0f}) → ({p1[0]:.0f}, {p1[1]:.0f})，长 {l['L']:.0f}px，两端都没碰到别的元素", '', where(t, l['bb'], l.get('m'), l.get('shot')), l['bb'], MAG, src=l.get('src'))
        by_text = {}
        for l, g in cross: by_text.setdefault(g['s'].strip(), (g, []))[1].append(l)
        for s_, (g, ls) in by_text.items():
            l = ls[0]
            add('⚠️', '线穿过文字', f"线 ({l['pts'][0][0]:.0f}, {l['pts'][0][1]:.0f}) → ({l['pts'][-1][0]:.0f}, {l['pts'][-1][1]:.0f}) 从字身上穿过" + (f'（{len(ls)} 条线）' if len(ls) > 1 else ''), s_[:24],
                where(t, (g['x0'], g['y0'], g['x1'], g['y1']), g.get('m'), g.get('shot')), (g['x0'], g['y0'], g['x1'], g['y1']), MAG, src=l.get('src'))
            for k in ls: boxes.append((k['bb'][0] * sc, k['bb'][1] * sc, k['bb'][2] * sc, k['bb'][3] * sc, MAG))
        for k, r in links:
            if k.get('missing'):
                add('❌', '标注没落到目标', f"锚点「{k['to']}」这一帧不存在（还没画、名字写错，或 anchor 写在 callout 之后）", f"callout → {k['to']}", {'t': round(t, 3), 'shot': scene_of(t), 'text': ''},
                    src=(fd.get('marks') or {}).get('callout:' + str(k['to'])))
                continue
            x, y = k['end']
            if r is None:
                add('❌', '标注没落到目标', f"锚点「{k['to']}」这一帧没有登记", f"callout → {k['to']}", where(t, (x - 4, y - 4, x + 4, y + 4), None, k.get('shot')), (x - 6, y - 6, x + 6, y + 6), src=k.get('src'))
            else:
                bx = (min(x, r['x']), min(y, r['y']), max(x, r['x'] + r['w']), max(y, r['y'] + r['h']))
                add('❌', '标注没落到目标', f"引线终点 ({x:.0f}, {y:.0f}) 不在目标 ({r['x']:.0f}, {r['y']:.0f}, {r['w']:.0f}×{r['h']:.0f}) 上", f"callout → {k['to']}",
                    where(t, (r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']), None, k.get('shot')), bx, src=k.get('src'))
        if boxes: flagged[t] = (small, boxes)
    global CHROME; CHROME = finish_subject(subj, W, H)
    return rows, flagged, subj


LV = {'❌': 0, '⚠️': 1, 'ℹ️': 2}


def summary_line(nb, nw, ni, where='报告'):
    """终端摘要的口径（版面审计、体检、render.py 同一句）：硬伤 N 条（❌ a、⚠️ b）；可选提示 M 条见报告"""
    return f'硬伤 {nb + nw} 条（❌ {nb}、⚠️ {nw}）；可选提示 {ni} 条见{where}'


def fmt_line(level, shot, t, src, text, kind, msg, n=1):
    """一条问题一行：❌ S05 · 12.3s · web/shots_05.js:27 · 「几十年内」 · 文字出框（右侧超出画面 18px）"""
    parts = [f'{level} {shot}', f'{t:.1f}s' if isinstance(t, (int, float)) else str(t)]
    if src: parts.append(src)
    if text: parts.append(f'「{text}」')
    parts.append(f'{kind}（{msg}）' if msg else kind)
    return ' · '.join(parts) + (f'　共 {n} 个取样点' if n > 1 else '')


def report(rows, flagged, subj, name, W, H):
    # 同一镜头里同一问题、同一段文字合并成一条，时刻并列；定位取第一次出现
    merged = {}
    for sid, t, level, kind, msg, text, loc, src, box in rows:
        e = merged.setdefault((sid, kind, text), {'shot': sid, 'kind': kind, 'issue': kind + '：' + msg if msg else kind, 'msg': msg, 'text': text, 'level': level,
                                                   'times': [], 'where': loc, 'src': src, 'box': box})
        e['times'].append(t); e['src'] = e['src'] or src
    for (sid, text), f in FITS.items():                              # 文字块放不下（textBlock 登记）：可选提示
        b = f.get('box') or {}
        bw, bh = (b.get('w', 0), b.get('h', 0)) if isinstance(b, dict) else (b[2], b[3]) if len(b) >= 4 else (0, 0)
        msg = f"box {bw:.0f}×{bh:.0f}px，照最小字号 {f.get('size', 0):.0f}px 画了，可能超出这块区域：要它待在区域里就删字、拆成两块，或给更大的 box"
        merged[(sid, '文字块放不下', text)] = {'shot': sid, 'kind': '文字块放不下', 'issue': '文字块放不下：' + msg, 'msg': msg, 'text': text[:24], 'level': 'ℹ️',
                                         'times': f['times'], 'where': None, 'src': f.get('src'), 'box': None}
    if RAW:                                                          # 直接 fillText 的字：整片一条提示
        (s0, t0, src0) = next(iter(RAW.values()))
        ex = '、'.join(f'「{k[:10]}」' for k in list(RAW)[:4]) + (' …' if len(RAW) > 4 else '')
        msg = f'{len(RAW)} 段字直接用 ctx.fillText / strokeText 画（{ex}）：出框、字号、压字照样查；要标装饰小字时用 deco(ctx, 原因, () => …) 包起来'
        merged[('全片', '直接用 fillText 画的字', '')] = {'shot': '全片', 'kind': '直接用 fillText 画的字', 'issue': msg, 'msg': msg, 'text': '', 'level': 'ℹ️',
                                                    'times': [t0], 'where': None, 'src': src0, 'box': None}
    items = sorted(merged.values(), key=lambda e: (LV.get(e['level'], 3), e['times'][0]))
    for e in items: e['line'] = fmt_line(e['level'], e['shot'], e['times'][0], e['src'], e['text'], e['kind'], e['msg'], len(e['times']))
    nb = sum(1 for e in items if e['level'] == '❌'); nw = sum(1 for e in items if e['level'] == '⚠️'); hard = [e for e in items if e['level'] in ('❌', '⚠️')]
    print(f'\n版面审计 {W}×{H}：取样 {len(sample_times())} 个时刻，' + summary_line(nb, nw, len(items) - len(hard), 'json'))
    for e in hard[:50]: print(e['line'])
    if len(hard) > 50: print(f'… 还有 {len(hard) - 50} 条，见 json')
    if not hard: print('没有发现版面硬伤。数字只能发现问题，不能证明好看：再看一遍总览图。')
    p = VIEW / f'{name}_layout.jpg'
    if flagged:
        ts = sorted(flagged)[:16]
        cols = 4 if W >= H else 5; th = (480 if W >= H else 300)
        ch = round(th * H / W); rows_n = (len(ts) + cols - 1) // cols
        sh = Image.new('RGB', (cols * th, rows_n * (ch + 16)), (32, 32, 32)); d = ImageDraw.Draw(sh)
        for j, t in enumerate(ts):
            im, boxes = flagged[t]; x, y = (j % cols) * th, (j // cols) * (ch + 16)
            im = im.copy(); dd = ImageDraw.Draw(im)
            for b in boxes: dd.rectangle(b[:4], outline=b[4], width=2)
            sh.paste(im, (x, y)); d.text((x + 4, y + ch + 2), f'{scene_of(t)}  {t:.2f}s', fill=(255, 220, 0))
        sh.save(p, quality=84); print('问题帧', p)
    elif p.exists():
        p.unlink()
    if DECO:
        print(f'装饰字豁免 {len(DECO)} 条（不按字号下限拦）：')
        for (sid, text, why), (ts, cap) in DECO.items(): print(f'  {sid}  {text}  字高 {cap:.0f}px  原因：{why}  时刻 {" ".join(f"{t:.2f}" for t in ts[:4])}')
    if any(e['kind'] == '字太小' for e in items):
        print('字太小：加大到下限以上。下限不能调低；刻意的装饰小字（背景水印、纹理）在绘制时标 deco，会列进报告。')
    if any(e['kind'] == '标注没落到目标' for e in items):
        print('标注没落到目标：画目标时用 anchor(ctx, 名字, x, y, w, h) 登记，标注用 callout(ctx, 名字, 起点) 画，终点由引擎算出。')
    jp = VIEW / f'{name}_layout.json'
    json.dump({'W': W, 'H': H, 'min_text': MIN_TEXT, 'n_samples': len(sample_times()), 'override_ignored': OVERRIDE, 'items': items,
               'subject': subj, 'chrome': CHROME, 'grid': list(grid_shape(W, H)), 'subject_min': SUBJECT_MIN[GENRE if GENRE in SUBJECT_MIN else 'explainer'],
               'acts': list(ACTS.values()), 'fits': [dict(v, shot=k[0]) for k, v in FITS.items()],
               'deco': [{'shot': sid, 'text': text, 'why': why, 'cap': round(cap, 1), 'times': ts} for (sid, text, why), (ts, cap) in DECO.items()],
               'sheet': str(p) if flagged else None}, open(jp, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    lease = gpu_slot() if uses_gpu() else contextlib.nullcontext()
    with lease, sync_playwright() as p, serve() as url:
        for fmt in FMTS:
            W, H = formats()[fmt]
            min_text = min(W, H) * (0.015 if GENRE == 'explainer' else 0.022)    # 锁定：按短边成比例，project.json 不能改
            OVERRIDE = (CFG.get('layout') or {}).get('min_text'); MIN_TEXT = min_text
            if OVERRIDE is not None: print(f'注意：project.json 的 layout.min_text = {OVERRIDE} 已不生效，字号下限固定为 {min_text:.0f}px（短边 × {0.015 if GENRE == "explainer" else 0.022}）。要小字就逐个标 deco。')
            b, pg, errs = open_page(p, url, fmt, init_script=INIT_JS)
            pg.evaluate(CAM_JS)
            pg.evaluate('window.__MB_OFF = true; window.__REC = true')
            rows, flagged, subj = audit(pg, W, H, min_text, errs)
            name = (NAME + (f'_{fmt}' if len(formats()) > 1 else '')) if NAME else out_name(fmt)[:-4]
            report(rows, flagged, subj, name, W, H)
            pe = [e for e in errs if not e.startswith('console.warning')]
            if pe: print('页面错误：', pe[:4])
            b.close()
        sys.stdout.flush(); os._exit(0)      # 结果已落盘；杀掉 Chrome 后 Playwright 收尾偶尔要等约 30 秒，直接退出
