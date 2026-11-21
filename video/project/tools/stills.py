"""静帧与总览（直接从网页取帧，不用渲整片）：
  python3 tools/stills.py S03                                 镜头 S03 的 0.3、0.6、0.9 处三帧 → frames/_view/S03.jpg（S03,S05 一次看几个镜头）
  python3 tools/stills.py S02@0.5,S02+1.2,b12,12.5            指定时刻，自动起名 → frames/_view/at_S02_0.5_S02p1.2_….jpg
  python3 tools/stills.py 名字 S02@0.5,S02+1.2,b12,12.5       指定时刻 → frames/_view/名字.jpg
        S02@0.5 = 镜头 S02 时长的 50% 处（@ 后只能写 0~1）   S02+1.2 = 镜头 S02 开始后 1.2 秒   b12 = 第 12 拍   12.5 = 全片第 12.5 秒
  第一个参数怎么理解（会打印实际的理解）：
        后面没有别的参数时：是镜头号（或逗号隔开的几个镜头号）→ 每个镜头三帧；是时刻列表 → 按时刻取帧、自动起名。
        后面还有时刻列表时：第一个参数是输出名。名字恰好是镜头号（例如 S01 0.3,0.75）时按镜头号理解：
        后面的裸数字是这个镜头时长的比例（0~1），等于 S01@0.3,S01@0.75；写 S02@0.5、b12 这类带前缀的时刻照常。
        要全片秒数时，名字换成不是镜头号的词（stills.py v1 12.5）；镜头内秒数写 S01+1.2。
  python3 tools/stills.py 名字 --all 0.3,0.7,0.95 [S01,S02]   每个镜头的若干比例处，拼成总览 frames/_view/名字_NN.jpg
  python3 tools/stills.py 名字 --every 0.5 [起 止]            每隔 0.5 秒一帧（或 --every beat 每拍一帧），拼成一张节奏总览
  python3 tools/stills.py 名字 --cuts [S03,S04]               转场逐帧条：每个镜头起点（第一个除外）的转场窗口里等距取 7 帧拼成一行 → 名字_cuts_NN.jpg
        窗口 = 新镜头开始画（t0 - pre）前 0.05 秒 到 旧镜头停止画（上一镜头 t1 + post）后 0.15 秒，至少覆盖 t0 ± 0.25 秒。
        看这张图：转场中间有没有两层画面半透明叠在一起，内容有没有溢出容器。
  python3 tools/stills.py 名字 --between b8-b12 [n]           指定拍区间里每两拍之间等距取 n 帧（默认 5）→ 名字_between_NN.jpg，用于一镜到底、变形片
        区间两端也可以写秒或 S02+1.2。每格标时刻和拍号。
  python3 tools/stills.py 名字 --trail S02@0.2-S02@0.8 [n]      洋葱皮：这段时间里等距取 n 帧（默认 8）叠成一张 → 名字_trail.jpg
        不动的部分只画一次，运动的部分一帧一个残影，越新越实。区间两端写法同上（秒、b12、S02+1.2）。
        看这张图：轨迹顺不顺、残影间距是不是先密后疏（缓动）、跟着走的元素是不是稍晚一点落位。
  python3 tools/stills.py 名字 --props [t1,t2,t3]              物件表：PROP 登记的每个物件单独画大，一个物件一行 → frames/_view/props.jpg
        每个物件按自然尺寸（PROP.名字.size）放大到约 800 像素高（一行三格放得进宽 1600 时），画 3 个时刻：
        镜头里第一次、中间、最后一次用 prop() 画它的那一刻（带上当时传的 o），没用过的画 t = 0、全片中点、结尾；也可以自己给 t。
        虚线框是自然尺寸的边界，框外留了一圈：画出框的部分（会被分区切掉）看得见。物件多于 3 个时续写 props_2.jpg……
        看这张图：部件有没有接上、比例对不对、线宽统一吗、轮廓清不清楚、有没有画出框。检查过再放进镜头。
  选项：--format 名字   --mb 开运动模糊（默认关，快）
自查只读 frames/_view/ 下的 JPEG。1080p PNG 一张 2–3 MB，连读十几张会撑爆对话请求，之后会话无法恢复。
"""
import sys, io, re, json, contextlib
if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from common import ROOT, serve, open_page, resolve_time, timeline, pop_format, formats, uses_gpu, gpu_slot, snap

ARGV = sys.argv[1:]
FMT = pop_format(ARGV)[0]
MB = '--mb' in ARGV
if MB: ARGV.remove('--mb')
VIEW = ROOT / 'frames' / '_view'; VIEW.mkdir(parents=True, exist_ok=True)
FW, FH = formats()[FMT]
PORT = FW < FH


def shoot(pg, jobs, prefix):
    out = []
    for label, t in sorted(jobs, key=lambda j: j[1]):          # 时间只能向前（shader 背景），按升序取
        pg.evaluate(f'render({t})')
        path = ROOT / 'frames' / f'{prefix}_{label}.png'; path.parent.mkdir(exist_ok=True)
        pg.screenshot(path=str(path)); out.append((label, t, path))
    return out


def grab(pg, t, width):
    """取一帧，直接缩成 PIL 图（不落盘）。直接读画布，不走浏览器截图（快约 5 倍）"""
    im = Image.open(io.BytesIO(snap(pg, t, 88))).convert('RGB')
    return im.resize((width, round(width * FH / FW)), Image.LANCZOS)


def sheet(items, name, cols, long_side):
    cw, ch = (long_side, round(long_side * FH / FW)) if FW >= FH else (round(long_side * FW / FH), long_side)
    rows = (len(items) + cols - 1) // cols
    sh = Image.new('RGB', (cols * cw, rows * (ch + 16)), (32, 32, 32)); d = ImageDraw.Draw(sh)
    for j, (label, t, path) in enumerate(items):
        x, y = (j % cols) * cw, (j // cols) * (ch + 16)
        sh.paste(Image.open(path).convert('RGB').resize((cw, ch), Image.LANCZOS), (x, y))
        d.text((x + 4, y + ch + 2), f'{label}  {t:.2f}s', fill=(255, 220, 0))
    p = VIEW / name; sh.save(p, quality=84); return p


def rows_sheet(rows, name, cols, cw):
    """rows = [(行标题, [(格标签, PIL 图), ...]), ...]。每行一个标题条，每格下面标签。PIL 默认字体不含中文，标题和标签只用英文和数字。"""
    ch = rows[0][1][0][1].size[1]
    sh = Image.new('RGB', (cols * cw, len(rows) * (ch + 34)), (32, 32, 32)); d = ImageDraw.Draw(sh)
    for r, (title, cells) in enumerate(rows):
        y = r * (ch + 34); d.text((4, y + 3), title, fill=(120, 220, 255))
        for c, (lab, im) in enumerate(cells):
            sh.paste(im, (c * cw, y + 16)); d.text((c * cw + 4, y + 18 + ch), lab, fill=(255, 220, 0))
    p = VIEW / name; sh.save(p, quality=84); return p


def draw_ranges(pg, tl):
    """每个镜头实际被画的 [a, z)：和 main.js 一样，读 SHOT.<id> 的 pre/post/a/b 和 project.json 的 transitions。"""
    return pg.evaluate('''(order) => {
      const TR = (window.PROJECT || {}).transitions || {};
      const trOf = i => { const s = order[i]; if (!order[i + 1]) return null; const v = TR[s.id] ?? TR.default ?? 'cut'; const o = typeof v === 'string' ? { type: v } : v; return o.type === 'cut' ? null : Object.assign({ dur: 0.5 }, o); };
      return order.map((S, i) => {
        const d = window.SHOT[S.id];
        let a = d && d.a !== undefined ? d.a : S.t0 - ((d && d.pre) || 0), z = d && d.b !== undefined ? d.b : S.t1 + ((d && d.post) || 0);
        const tin = i > 0 ? trOf(i - 1) : null, tout = trOf(i);
        if (tin) a = Math.min(a, S.t0 - tin.dur / 2);
        if (tout) z = Math.max(z, S.t1 + tout.dur / 2);
        return { id: S.id, a, z };
      });
    }''', sorted(tl['scenes'].values(), key=lambda s: s['t0']))


PROP_USE_JS = r"""() => {                                           // 记下镜头里每次 prop() 画了哪个物件、用的 t 和 o
  if (typeof window.prop !== 'function' || window.prop.__used) return;
  const o0 = window.prop; window.__PROPUSE = {};
  window.prop = function (ctx, name, box, o) {
    try { const L = window.__PROPUSE[name] || (window.__PROPUSE[name] = []);
      if (!L.length || L[L.length - 1][0] !== window.__PT) L.push([window.__PT, (o && o.t !== undefined) ? o.t : window.__PT, JSON.parse(JSON.stringify(o || {})), (typeof SHOT_NOW !== 'undefined' && SHOT_NOW) || null]); } catch (e) {}
    return o0.apply(this, arguments);
  };
  window.prop.__used = true;
}"""
PROP_DRAW_JS = r"""([name, t, o, H, maxW]) => {                          // 按自然尺寸放大画一个物件，四周留一圈，虚线框是自然尺寸的边界
  const R = typeof PROP !== 'undefined' ? PROP : window.PROP, P = R[name], [w, h] = P.size;
  const pad = 0.08, s = Math.min(H / (h * (1 + 2 * pad)), maxW / (w + 2 * pad * h)), m = Math.round(pad * h * s);
  const cv = document.createElement('canvas'); cv.width = Math.round(w * s) + 2 * m; cv.height = Math.round(h * s) + 2 * m;
  const g = cv.getContext('2d'); g.fillStyle = (typeof COL !== 'undefined' && COL.bg) || '#ffffff'; g.fillRect(0, 0, cv.width, cv.height);
  let err = null; g.save(); g.translate(m, m); g.scale(s, s);
  try { P(g, t, o || {}); } catch (e) { err = String(e && e.message || e); } g.restore();
  g.setLineDash([10, 7]); g.lineWidth = 2; g.strokeStyle = 'rgba(230,40,170,0.75)'; g.strokeRect(m, m, Math.round(w * s), Math.round(h * s));
  return [cv.toDataURL('image/jpeg', 0.9), err, s];
}"""


def props_mode(pg, tl, prefix):
    """物件表：每个物件一行、3 个时刻，标物件名、自然尺寸、放大倍数和时刻"""
    import numpy as np, base64
    from common import font
    reg = pg.evaluate("() => { const R = typeof PROP !== 'undefined' ? PROP : window.PROP; const L = window.__PROPS;"
                      " if (Array.isArray(L) && L.length) return L.map(x => typeof x === 'string' ? { name: x, size: R && R[x] && R[x].size } : x);"
                      " return R ? Object.keys(R).map(k => ({ name: k, size: R[k] && R[k].size })) : null; }")
    if not reg:
        print('没有登记物件。主角物件（角色、器物、场景里的主体）先登记再进镜头：\n'
              '  PROP.cat = function (ctx, t, o) { /* 按自然尺寸画，原点在左上角；t 算物件自己的动作，o 是镜头传来的参数 */ };\n'
              '  PROP.cat.size = [600, 480];          // 自然尺寸，必填\n'
              '  镜头里：prop(ctx, \'cat\', 分区, { mood: \'happy\' });   // 按 fit 放满分区\n'
              '写在 shots_00_*.js（共用文件）里，再跑 python3 tools/stills.py 名字 --props 单独画大检查。')
        return
    bad = [r['name'] for r in reg if not (isinstance(r.get('size'), list) and len(r['size']) == 2)]
    if bad: print(f'这些物件没有写 size，跳过：{", ".join(bad)}（写 PROP.名字.size = [宽, 高]）')
    reg = [r for r in reg if r['name'] not in bad]
    if not reg: return
    i = ARGV.index('--props'); fixed = None
    if len(ARGV) > i + 1 and not ARGV[i + 1].startswith('-'): fixed = [resolve_time(tl, x) for x in ARGV[i + 1].split(',')]
    total = tl['total']; use = {}
    if fixed is None:                                                   # 扫一遍全片（每 0.25 秒），记下每个物件在哪些时刻被画、用的 t 和 o
        pg.evaluate(PROP_USE_JS); t = 0.0
        while t < total - 1e-6:
            pg.evaluate(f'window.__PT = {t}'); pg.evaluate(f'render({t})'); t = round(t + 0.25, 4)
        use = pg.evaluate('window.__PROPUSE || {}')
    W_ROW, GAP, LAB = 1600, 8, 22
    rows = []
    for r in reg:
        name, (w, h) = r['name'], r['size']
        L = use.get(name) or []
        if fixed is not None: picks = [(t, t, {}, None) for t in fixed]
        elif L: picks = [L[0], L[len(L) // 2], L[-1]] if len(L) >= 3 else L
        else: picks = [(0.0, 0.0, {}, None), (total / 2, total / 2, {}, None), (total, total, {}, None)]
        n = len(picks); maxW = (W_ROW - GAP * (n - 1)) / n
        cells = []
        for pt, t, o, sh in picks:
            url, err, sc = pg.evaluate(PROP_DRAW_JS, [name, t, o, 800, maxW])
            im = Image.open(io.BytesIO(base64.b64decode(url.split(',', 1)[1]))).convert('RGB')
            if err: print(f'{name} 在 t = {t:.2f} 画的时候报错：{err}')
            cells.append((im, f't = {t:.2f}s' + (f'（{sh} {pt:.2f}s）' if sh else '') + (f'  o = {json.dumps(o, ensure_ascii=False)[:40]}' if o else ''), err, sc))
        rows.append((f'{name}　自然尺寸 {w:g}×{h:g}　放大 ×{cells[0][3]:.2f}' + ('　（镜头里没有用 prop() 画过它）' if fixed is None and not L else ''), cells))
    f, fb = font(15), font(18); out = []
    for g0 in range(0, len(rows), 3):                                 # 每张最多 3 个物件，图不至于太高
        part = rows[g0:g0 + 3]
        hs = [max(c[0].height for c in cells) for _, cells in part]
        sh_ = Image.new('RGB', (W_ROW, sum(h_ + LAB * 2 + 10 for h_ in hs)), (32, 32, 32)); d = ImageDraw.Draw(sh_); y = 0
        for (title, cells), h_ in zip(part, hs):
            d.text((6, y + 2), title, fill=(120, 220, 255), font=fb); x = 0
            for im, lab, err, _ in cells:
                sh_.paste(im, (x, y + LAB)); d.text((x + 4, y + LAB + h_ + 3), lab if not err else '报错：' + err[:60], fill=(255, 220, 0) if not err else (255, 90, 90), font=f)
                x += im.width + GAP
            y += h_ + LAB * 2 + 10
        p = VIEW / ('props.jpg' if g0 == 0 else f'props_{g0 // 3 + 1}.jpg'); sh_.save(p, quality=86); out.append(p)
    for p in out: print(p)
    print('看每个物件：部件有没有接上、比例对不对、线宽统一吗、轮廓清不清楚、有没有画出虚线框（出框的部分在镜头里会被切掉）。')


def cuts_mode(pg, tl, prefix):
    order = sorted(tl['scenes'].values(), key=lambda s: s['t0']); R = draw_ranges(pg, tl)
    want = None
    i = ARGV.index('--cuts')
    if len(ARGV) > i + 1 and not ARGV[i + 1].startswith('-'): want = ARGV[i + 1].split(',')
    wins = []                                                     # (标题, t0, [7 个时刻])
    for k in range(1, len(order)):
        S = order[k]
        if want and S['id'] not in want: continue
        lo = min(R[k]['a'] - 0.05, S['t0'] - 0.25); hi = max(R[k - 1]['z'] + 0.15, S['t0'] + 0.25)
        lo = max(0.0, lo); hi = min(tl['total'] - 1e-3, hi)
        ts = [lo + (hi - lo) * j / 6 for j in range(7)]
        wins.append((f"{order[k - 1]['id']} > {S['id']}   cut {S['t0']:.2f}s   new shot starts drawing {R[k]['a']:.2f}s   old shot stops {R[k - 1]['z']:.2f}s", S['t0'], ts))
    if not wins: sys.exit('没有可看的转场（只有一个镜头，或 --cuts 后写的镜头号不存在）')
    cw = 270 if not PORT else 180
    # 时间只能向前（shader 背景）：全部时刻升序取，再按行归位
    shots = {}
    for _, _, ts in wins:
        for t in ts: shots[round(t, 4)] = None
    for t in sorted(shots): shots[t] = grab(pg, t, cw)
    rows = [(title, [(f'{t:.2f}s ({t - t0:+.2f})', shots[round(t, 4)]) for t in ts]) for title, t0, ts in wins]
    per = 6 if not PORT else 3
    for g in range(0, len(rows), per):
        print(rows_sheet(rows[g:g + per], f'{prefix}_cuts_{g // per:02d}.jpg', 7, cw))
    print('每格下面是时刻（括号里是相对切换点 cut 的秒数）。看转场中间：有没有两层半透明叠在一起、内容有没有溢出容器或被裁掉。')


def trail_image(pg, ta, tz, n, width=None):
    """[ta, tz] 等距 n 帧叠成洋葱皮图（PIL）。背景 = 各帧逐像素中位数；每帧和背景差异明显的像素按由旧到新、由淡到实盖上去。"""
    import numpy as np
    width = width or (1280 if FW >= FH else 720)
    ts = [ta + (tz - ta) * k / max(1, n - 1) for k in range(n)]
    fr = [np.asarray(grab(pg, t, width)).astype(np.float32) for t in ts]
    base = np.median(np.stack(fr), 0); out = base.copy()
    for k, f in enumerate(fr):
        m = (np.abs(f - base).max(-1) > 24)[..., None]; a = 0.25 + 0.75 * (k + 1) / n
        out = np.where(m, out * (1 - a) + f * a, out)
    im = Image.fromarray(out.clip(0, 255).astype('uint8')); d = ImageDraw.Draw(im)
    lab = f'trail {ta:.2f}s - {tz:.2f}s  x{n}  (old = faint, new = solid)'
    d.rectangle([0, 0, 8 * len(lab) + 10, 18], fill=(0, 0, 0)); d.text((5, 3), lab, fill=(255, 220, 0))
    return im


def trail_mode(pg, tl, prefix):
    i = ARGV.index('--trail'); rg = ARGV[i + 1]
    n = int(ARGV[i + 2]) if len(ARGV) > i + 2 and ARGV[i + 2].isdigit() else 8
    m = re.match(r'^(.+?)-(?=[Sb\d])(.+)$', rg)
    if not m: sys.exit('区间写成 起-止，例如 2.0-3.5、b8-b12、S02@0.2-S02@0.8')
    ta, tz = resolve_time(tl, m.group(1)), min(resolve_time(tl, m.group(2)), tl['total'] - 1e-3)
    if tz <= ta: sys.exit('区间的终点要晚于起点')
    p = VIEW / f'{prefix}_trail.jpg'; trail_image(pg, ta, tz, n).save(p, quality=86); print(p)


def between_mode(pg, tl, prefix):
    i = ARGV.index('--between'); rng = ARGV[i + 1]
    n = int(ARGV[i + 2]) if len(ARGV) > i + 2 and ARGV[i + 2].isdigit() else 5
    if '-' not in rng[1:]: sys.exit('区间写成 b8-b12（也可以写秒：4-6）')
    a_s, z_s = rng.split('-', 1)
    ta, tz = resolve_time(tl, a_s), resolve_time(tl, z_s)
    beat = tl.get('beat')
    if not beat: sys.exit('时间轴里没有拍长（beat），--between 只用于节拍时间轴')
    off = tl.get('offset', 0)
    k0 = round((ta - off) / beat, 4); k1 = round((tz - off) / beat, 4)
    nb = int(round(k1 - k0))
    if nb < 1: sys.exit('区间至少要隔一拍')
    cw = 270 if not PORT else 180
    rows, times = [], []
    for b in range(nb):
        tb = off + (k0 + b) * beat
        times += [tb + beat * j / n for j in range(n)]
    shots = {round(t, 4): grab(pg, min(t, tl['total'] - 1e-3), cw) for t in times}
    for b in range(nb):
        tb = off + (k0 + b) * beat
        cells = [(f'b{k0 + b + j / n:.2f}  {tb + beat * j / n:.2f}s', shots[round(tb + beat * j / n, 4)]) for j in range(n)]
        rows.append((f'beat {k0 + b:g} > {k0 + b + 1:g}', cells))
    per = 6 if not PORT else 3
    for g in range(0, len(rows), per):
        print(rows_sheet(rows[g:g + per], f'{prefix}_between_{g // per:02d}.jpg', n, cw))
    print('看每行的相邻格：中间过程有没有两层半透明叠着、内容有没有溢出容器、形状是不是连续变形而不是跳变。')


MODES = ('--props', '--cuts', '--trail', '--between', '--all', '--every')
TIME_RE = re.compile(r'^(?:\w+@[\d.]+|\w+\+[\d.]+|b[\d.]+|\d+(?:\.\d+)?)$')
NUM_RE = re.compile(r'^\d+(?:\.\d+)?$')
SHOT_FR = (0.3, 0.6, 0.9)


def plain_jobs(tl):
    """不带模式参数时：判别第一个参数是镜头号、时刻列表还是输出名（规则见文件头），打印实际的理解。返回 (输出名, [(格标签, 时刻)], 每行几格)"""
    ids, pos = tl['scenes'], ARGV
    lab = lambda x: x.replace('@', '_').replace('+', 'p')
    times = lambda xs: [(lab(x), resolve_time(tl, x)) for x in xs]
    usage = ('写法：stills.py S03（这个镜头三帧）；stills.py S03@0.5,b12（指定时刻，自动起名）；stills.py 名字 S03@0.5,b12。'
             f'镜头号可选：{", ".join(ids)}。python3 tools/stills.py --help 看全部用法')
    if len(pos) == 1:
        items = pos[0].split(',')
        if all(x in ids for x in items):
            print(f'理解为镜头号：{"、".join(items)}，{"每个镜头" if len(items) > 1 else "这个镜头"}取 {"、".join(map(str, SHOT_FR))} 处三帧')
            return '_'.join(items)[:60], [(f'{x}_{f}', resolve_time(tl, f'{x}@{f}')) for x in items for f in SHOT_FR], 3
        if all(TIME_RE.match(x) for x in items):
            name = 'at_' + re.sub(r'[^\w.]+', '_', lab(pos[0]))[:60]
            print(f'理解为时刻列表：{pos[0]}，输出名自动起为 {name}')
            return name, times(items), None
        sys.exit(f'看不懂 {pos[0]}：既不是镜头号，也不是时刻列表。' + usage)
    if len(pos) != 2: sys.exit(f'看不懂参数：{" ".join(pos)}。' + usage)
    name, items = pos[0], pos[1].split(',')
    if name in ids:
        bare = [x for x in items if NUM_RE.match(x)]
        if any(float(x) > 1 for x in bare):
            sys.exit(f'{name} 是镜头号，后面的裸数字按这个镜头时长的比例（0~1）理解，{",".join(x for x in bare if float(x) > 1)} 超出了。'
                     f'要全片秒数，输出名换成不是镜头号的词（stills.py v1 {pos[1]}）；镜头内秒数写 {name}+1.2')
        if bare:
            items = [f'{name}@{x}' if NUM_RE.match(x) else x for x in items]
            print(f'理解为镜头号：裸数字按镜头 {name} 时长的比例取 → {",".join(items)}；输出名 {name}')
        else:
            print(f'理解为输出名：{name}（恰好是镜头号；时刻照写的取：{pos[1]}）')
    return name, times(items), None


if __name__ == '__main__':
    tl = timeline()
    plain = not any(m in ARGV for m in MODES)
    if plain: prefix, jobs, per_row = plain_jobs(tl)
    else: prefix = ARGV[0]
    lease = gpu_slot() if uses_gpu() else contextlib.nullcontext()
    with lease, sync_playwright() as p, serve() as url:
        b, pg, errs = open_page(p, url, FMT)
        if not MB: pg.evaluate('window.__MB_OFF = true')
        if '--props' in ARGV:
            props_mode(pg, tl, prefix)
        elif '--cuts' in ARGV:
            cuts_mode(pg, tl, prefix)
        elif '--trail' in ARGV:
            trail_mode(pg, tl, prefix)
        elif '--between' in ARGV:
            between_mode(pg, tl, prefix)
        elif '--all' in ARGV:
            i = ARGV.index('--all'); fr = [float(x) for x in ARGV[i + 1].split(',')]
            S = sorted(tl['scenes'].values(), key=lambda s: s['t0'])
            if len(ARGV) > i + 2: S = [s for s in S if s['id'] in ARGV[i + 2].split(',')]
            jobs = [(f"{s['id']}_{f:.2f}", s['t0'] + min(f, 0.999) * s['dur']) for s in S for f in fr]
            items = shoot(pg, jobs, prefix)
            per = 12 if FW >= FH else 10
            for g in range(0, len(items), per):
                print(sheet(items[g:g + per], f'{prefix}_{g // per:02d}.jpg', 4 if FW >= FH else 5, 480 if FW >= FH else 400))
        elif '--every' in ARGV:
            i = ARGV.index('--every'); st = tl['beat'] if ARGV[i + 1] == 'beat' else float(ARGV[i + 1])
            a = float(ARGV[i + 2]) if len(ARGV) > i + 3 else 0.0; z = float(ARGV[i + 3]) if len(ARGV) > i + 3 else tl['total'] - 1e-3
            ts = []; t = a
            while t <= z + 1e-9: ts.append(round(t, 4)); t += st
            items = shoot(pg, [(f'{k:03d}', t) for k, t in enumerate(ts)], prefix)
            cols = 8 if FW >= FH else 10
            for g in range(0, len(items), cols * 6):
                print(sheet(items[g:g + cols * 6], f'{prefix}_{g // (cols * 6):02d}.jpg', cols, 320 if FW >= FH else 300))
        else:
            items = shoot(pg, jobs, prefix)
            cols = per_row or (2 if len(items) > 1 else 1)
            print(sheet(items, f'{prefix}.jpg', cols, 640 if cols == 3 else 960 if cols == 2 else 1280))
        if errs: print('页面错误：', errs[:4])
        b.close()
