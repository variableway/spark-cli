/* =========================================================
   core.js —— 通用底座：画幅、主题、缓动、弹簧（含循环版、拍点入场）、衰减、节拍、画面事件、镜头矩阵、持续运动（drift、idle）、
   版面分区、物件表（PROP、prop）、图表比例尺、锚点与标注（anchor、callout、pin）、颜色、文字与文字块、字幕层、图片、应用窗口、光标、碎片拼合、音效登记、后期层
   合同：这里的函数只依赖传入的时间 t，不保存帧间状态；随机数一律用 rng(种子)。
   目录（一行用途 + 最短例子；详细参数见各节注释）：
     版面   safeBox()                        安全区矩形 {x, y, w, h}（也带 x0, y0, x1, y1）；字幕层开着时底边让出字幕带   const B = safeBox();
            split(box, dir, parts, gap)      按权重切成几块，'row' 左到右、'col' 上到下             const [L, R] = split(B, 'row', [3, 2], 40 * U);
            grid(box, cols, rows, gap)       等分网格，按行优先                                      const cells = grid(R, 2, 3, 24 * U);
            inset(box, m)                    四边收进 m（或 [上, 右, 下, 左]）                       const P = inset(L, 30 * U);
            fit(box, w, h, o)                把自然尺寸 w×h 的物件等比放进 box，返回 {x, y, w, h, s}   const f = fit(L, 600, 420, { align: 'bottom' });
     物件   PROP.名字 = (ctx, t, o) => {}    登记主角物件：按自然尺寸画，原点在左上角；.size 必填      PROP.cat = (ctx, t) => {...}; PROP.cat.size = [600, 480];
            prop(ctx, name, box, o)          把登记的物件 fit 进 box 再画，返回 fit 的结果           const f = prop(ctx, 'cat', L, { align: 'bottom' });
     颜色   parseColor(c)                    任何 CSS 颜色 → [r, g, b, a]（#rgb、#rrggbb、#rrggbbaa、rgb()、rgba()…） const [r, g, b] = parseColor(COL.acc);
            hexA(c, a) / mixHex(c1, c2, u)   改透明度 / 混色；输入任何 CSS 颜色，结果可以继续嵌套     hexA(mixHex(COL.ink, COL.acc, u), 0.6)
     文字   textBlock(ctx, text, box, o)     自动断行、定字号、对齐、入场的一块字                    textBlock(ctx, '水从根部进来', R, { role: 'title', t, at: ph('S02', 0) });
            textBlockMeasure(text, box, o)   同样的排版，只量不画                                    const m = textBlockMeasure(s, R, { role: 'body' }); m.h
            MIN_TEXT_PX                      可读下限（屏幕字高 px，和体检「字太小」同口径；只用来定 textBlock 的默认最小字号，不强制）
            txt / riseLine / slamLine / typeOn / rollWords / measure / wrap / fitSize   单行文字（见「文字」一节）
     事件   act(t, at, o)                    一个短句对应的画面动作，返回 0..1，时长默认按短句算        const u = act(t, ph('S03', 1), { name: '水柱上升' });
     时间   b(n) 第 n 拍；ph(id, k)、phE(id, k) 第 k 个短句的起止；enter、land、decay、inout、spring、springTo、springLoop、stagger、follow
     镜头   screen(ctx)、cam(ctx, cx, cy, z, rot)、camKeys(keys, t)、drift(t, S)、handheld、idle
     图表   chartScale({data, box, min, max})；anchor(ctx, name, x, y, w, h) + callout(ctx, name, from, o)；pin(ctx, C, v, o)
     图片   img、seqFrame、appWindow、shatter、cursor；形状 rrect、drawPath；背景 fillBg、glow；后期 SHAKES、FLASH、CUTS、FAST；音效 EV
     字幕   project.json 的 "subtitles": {"burn": true, "langs": ["zh", "en"]}：引擎按配音短句在底部字幕带画字幕，镜头里不用写（见「字幕层」一节）
   这些函数都是可选的工具，镜头里也可以直接用画布 API 画。几个省事的用法：
   标注用 anchor(ctx, '名字', x, y, w, h) 登记目标，再 callout(ctx, '名字', 起点, {p}) 画引线，终点由锚点算出，镜头推近也跟得上；
   图表上的数值标记用 pin(ctx, C, 数值, {at, label})，位置由 chartScale 算出。用法和例子见「锚点与标注」一节。
   split / grid 分区、fit 按自然尺寸放物件、textBlock 按区域定字号，换画幅时镜头代码不用改。
   PROP 登记的物件可以用 tools/stills.py --props 单独画大检查，镜头里 prop(ctx, 名字, 分区) 放进去。
   ========================================================= */
'use strict';
// ---------------------------------------------------------------- 画幅：由 project.json 的 canvas / formats 决定，?format=名字 选择
const PROJECT = window.PROJECT || {};
const FMT = new URLSearchParams(location.search).get('format') || PROJECT.default_format || null;
const _SIZE = (FMT && PROJECT.formats && PROJECT.formats[FMT]) || PROJECT.canvas || { w: 1920, h: 1080 };
const W = _SIZE.w, H = _SIZE.h;
const PORTRAIT = H > W, SQUARE = W === H;
const U = Math.min(W, H) / 1080;            // 版面单位：1080p 横版里 1U = 1px，竖版、方形按短边等比
const vw = p => W * p / 100, vh = p => H * p / 100;
{ const c = document.getElementById('c'); c.width = W; c.height = H; c.style.width = W + 'px'; c.style.height = H + 'px'; }

window.SHOT = window.SHOT || {};
const SHOT = window.SHOT;

// ---------------------------------------------------------------- 主题：配色和字体写在 project.json 的 theme，引擎不给颜色默认值
// 背景和配色是这支片子的设计决定（按题材和观众定），引擎不替片子选；缺了 bg 就没有背景可画，所以缺了就停下。
// 必填 bg、ink、acc（#RRGGBB）；ink2（次要文字）、dim（暗线、底纹）缺省时由 ink 和 bg 混出来；片子自己的颜色（water、leaf……）随便加。
// 字体缺省：display、body 用系统字体（中文由系统回落到苹方等），mono、serif 用模板自带的 JetBrains Mono、Instrument Serif。
const TH = PROJECT.theme || {};
const COL = (() => {
  const c = Object.assign({}, TH.colors || {}), long = v => typeof v === 'string' && /^#[0-9a-f]{3}$/i.test(v) ? '#' + [...v.slice(1)].map(x => x + x).join('') : v;
  for (const k of Object.keys(c)) c[k] = long(c[k]);
  const miss = ['bg', 'ink', 'acc'].filter(k => !c[k]), bad = ['bg', 'ink', 'acc'].filter(k => c[k] && !/^#[0-9a-f]{6}$/i.test(c[k]));
  if (miss.length || bad.length) {
    const m = (miss.length ? `project.json 的 theme.colors 缺少 ${miss.join('、')}。` : `project.json 的 theme.colors 里 ${bad.join('、')} 要写成 #RRGGBB。`) +
      '按题材和观众定色调和背景，写进 project.json 的 theme.colors（"colors": {"bg": "#RRGGBB", "ink": "#RRGGBB", "acc": "#RRGGBB"}），再运行 tools/timeline.py';
    window.__FATAL = m; throw new Error(m);
  }
  const mix = (a, b, u) => '#' + [16, 8, 0].map(s => Math.round((parseInt(a.slice(1), 16) >> s & 255) * (1 - u) + (parseInt(b.slice(1), 16) >> s & 255) * u).toString(16).padStart(2, '0')).join('');
  if (!c.ink2) c.ink2 = mix(c.ink, c.bg, 0.4);
  if (!c.dim) c.dim = mix(c.ink, c.bg, 0.8);
  return c;
})();
const FONT = Object.assign({ display: 'system-ui', body: 'system-ui', mono: 'JetBrains Mono', serif: 'Instrument Serif' }, TH.fonts || {});
const _ff = f => f.split(',').map(s => s.trim()).map(s => /\s/.test(s) && !/^["']/.test(s) ? `"${s}"` : s).join(', ');
const F = {
  d: (s, w = 800) => `${w} ${s}px ${_ff(FONT.display)}`,
  b: (s, w = 500) => `${w} ${s}px ${_ff(FONT.body)}`,
  m: (s, w = 500) => `${w} ${s}px ${_ff(FONT.mono)}`,
  s: (s, it = true, w = 400) => `${it ? 'italic ' : ''}${w} ${s}px ${_ff(FONT.serif)}`,
};

// ---------------------------------------------------------------- 数学与缓动
const clamp = (x, a = 0, c = 1) => Math.max(a, Math.min(c, x));
const lerp = (a, c, u) => a + (c - a) * u;
const prog = (t, a, d) => clamp((t - a) / d);
const smooth = u => u * u * (3 - 2 * u);
const E = {
  lin: u => u,
  out2: u => 1 - (1 - u) * (1 - u), out3: u => 1 - Math.pow(1 - u, 3), out4: u => 1 - Math.pow(1 - u, 4), out5: u => 1 - Math.pow(1 - u, 5),
  in2: u => u * u, in3: u => u * u * u, in4: u => u * u * u * u,
  inOut2: u => u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2,
  inOut3: u => u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2,
  inOut5: u => u < .5 ? 16 * Math.pow(u, 5) : 1 - Math.pow(-2 * u + 2, 5) / 2,
  outExpo: u => u >= 1 ? 1 : 1 - Math.pow(2, -10 * u),
  inExpo: u => u <= 0 ? 0 : Math.pow(2, 10 * u - 10),
  inOutExpo: u => u <= 0 ? 0 : u >= 1 ? 1 : u < .5 ? Math.pow(2, 20 * u - 10) / 2 : (2 - Math.pow(2, -20 * u + 10)) / 2,
  outBack: (u, s = 1.70158) => 1 + (s + 1) * Math.pow(u - 1, 3) + s * Math.pow(u - 1, 2),
  inOutSine: u => -(Math.cos(Math.PI * u) - 1) / 2,
};
// 阻尼弹簧的闭式解：t 秒后从 0 到 1 的位移（可过冲）。f 频率 Hz，z 阻尼比（<1 会回弹）
function spring(t, f = 2.0, z = 0.55) {
  if (t <= 0) return 0;
  const w = 2 * Math.PI * f;
  if (z < 1) { const wd = w * Math.sqrt(1 - z * z); return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + z * w / wd * Math.sin(wd * t)); }
  return 1 - Math.exp(-w * t) * (1 + w * t);
}
// 多段弹簧叠加：keys = [[t0, 目标值], ...]，每到一个时刻就从上一个目标弹向新目标；结果只由 t 决定
function springTo(t, keys, f = 2.0, z = 0.6) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], f, z);
  return v;
}
// 循环片的 springTo：keys 的时刻都在 [0, period) 内、按时间升序，目标值首尾相接（最后一个目标之后回到第一个）。
// 每个关键点只叠加它「最近一次发生」的弹簧残差，上一圈末尾没走完的弹簧会继续走进下一圈的开头，所以 t 和 t+period 的位置、速度都相同。
// springTo 做不到这点：它在 t=0 时不包含上一圈的尾巴，首尾会顿一下。keys 的第 3、4 项可单独指定该点的 f、z。
function springLoop(t, keys, period, f = 2.0, z = 0.6) {
  t = ((t % period) + period) % period; const n = keys.length;
  let v = keys[n - 1][1];
  for (const k of keys) if (k[0] <= t) v = k[1];
  for (let i = 0; i < n; i++) {
    const d = keys[i][1] - keys[(i + n - 1) % n][1]; if (!d) continue;
    let lt = t - keys[i][0]; if (lt < 0) lt += period;
    v += d * (spring(lt, keys[i][2] ?? f, keys[i][3] ?? z) - 1);
  }
  return v;
}
// ---------------------------------------------------------------- follow：一个量带延迟和弹性地跟随另一个量
// 用于：文字、图标、光标、阴影、标签跟着一个运动的主体走，主体停下时它们稍晚一点、晃一下才落定。
//   follow(t, leader, o)   leader = (t) => 数 或 (t) => [x, y, ...]（主体的位置，必须也只由 t 决定）
//   o.delay 延迟秒数（默认 0，跟随者追的是 leader(t - delay)）；o.f 弹簧频率 Hz（默认 3，越大跟得越紧）；
//   o.z 阻尼比（默认 0.7，<1 会过冲回弹，1 不过冲）。
// 纯函数：每次从 t - delay - 回看窗口 处「跟随者与主体重合、速度相同」开始，按固定步长用四阶龙格-库塔积分阻尼弹簧到 t，不读写帧间状态，
// 所以直接跳到任意一帧和顺序渲染结果完全相同。回看窗口按 f、z 自动取（弹簧的偏差衰减到约十万分之一，最长 12 秒），
// 结果与窗口长短无关。同一帧里相同参数的调用有缓存（按 t 清空）。
// 高级选项（一般不用）：o.window 手动指定回看秒数（太短时结果会随窗口变）；o.step 积分步长（默认随 f 自动取，见 followStep）。
// 例：const P = t => camKeys(KEYS, t); const [lx, ly] = follow(t, P, { delay: 0.08, f: 2.5, z: 0.5 });
const _FOL = { t: NaN, m: new Map() };
const _fshow = v => typeof v === 'string' ? `字符串 "${v}"` : v === null ? 'null' : v === undefined ? 'undefined' : Array.isArray(v) ? `数组 ${JSON.stringify(v)}` : typeof v === 'number' ? `数 ${v}` : `${typeof v} ${String(v)}`;
function followWindow(f, z) {
  const w = 2 * Math.PI * f, sig = z < 1 ? z * w : w * (z - Math.sqrt(z * z - 1));   // 偏差的衰减速率（过阻尼取慢的那一支）
  return clamp(11.5 / sig, 0.5, 12);                                                   // e^-11.5 ≈ 1e-5
}
// 默认步长随 f 变：频率低的弹簧变化慢，步子可以大（四阶龙格-库塔积分，f = 3 时 1/72 秒，f ≤ 1.25 时 1/30 秒），回看窗口长时也不慢。
function followStep(f) { return clamp(1 / (24 * f), 1 / 240, 1 / 30); }
function follow(t, leader, o = {}) {
  if (typeof leader !== 'function') throw new Error('follow 的第二个参数要是函数 (t) => 数 或 (t) => [x, y]，收到的是 ' + _fshow(leader));
  if (typeof t !== 'number' || !isFinite(t)) throw new Error('follow 的时间 t 要是有限的数，收到的是 ' + _fshow(t));
  const delay = o.delay ?? 0, f = o.f ?? 3, z = o.z ?? 0.7, step = o.step ?? followStep(f);
  const chk = [['delay', delay, v => v >= 0, '≥ 0'], ['f', f, v => v > 0, '> 0'], ['z', z, v => v > 0, '> 0'], ['step', step, v => v > 0 && v <= 0.05, '在 (0, 0.05] 之间']];
  if (o.window !== undefined) chk.push(['window', o.window, v => v > 0, '> 0']);
  for (const [k, v, ok, need] of chk)
    if (typeof v !== 'number' || !isFinite(v) || !ok(v)) throw new Error(`follow 的 o.${k} 要是${need}的数，收到的是 ${_fshow(v)}`);
  const win = o.window ?? followWindow(f, z), n = Math.ceil(win / step - 1e-9), h = win / n;
  if (f * h > 0.3) throw new Error(`follow 的 f=${f} 对步长 ${h.toFixed(4)} 秒太大，积分会不稳；需要 step < 0.3 / f，调小 o.step 或 f`);
  if (t !== _FOL.t) { _FOL.t = t; _FOL.m.clear(); }
  let byL = _FOL.m.get(leader); if (!byL) _FOL.m.set(leader, byL = new Map());
  const key = delay + '|' + f + '|' + z + '|' + win + '|' + step, hit = byL.get(key); if (hit !== undefined) return Array.isArray(hit) ? hit.slice() : hit;
  const t0 = t - delay - win, v0 = leader(t0), vec = Array.isArray(v0);
  if (!vec && typeof v0 !== 'number') throw new Error('follow 的 leader 要返回数或数组，收到的是 ' + _fshow(v0));
  const x = vec ? v0.map(Number) : [v0], d = x.length, eps = Math.min(step, 1e-3), p1 = vec ? leader(t0 + eps) : [leader(t0 + eps)];
  const v = x.map((xi, j) => (p1[j] - xi) / eps), w = 2 * Math.PI * f, w2 = w * w, c = 2 * z * w;
  // 四阶龙格-库塔：主体在每步的起点、中点、终点各取一次（终点留给下一步当起点）
  const A = (gx, xx, vv) => w2 * (gx - xx) - c * vv;
  let ga = vec ? v0 : [v0];
  for (let k = 1; k <= n; k++) {
    const sm = leader(t0 + (k - 0.5) * h), se = leader(t0 + k * h), gm = vec ? sm : [sm], ge = vec ? se : [se];
    for (let j = 0; j < d; j++) {
      const x0 = x[j], u0 = v[j];
      const k1x = u0, k1v = A(ga[j], x0, u0);
      const k2x = u0 + k1v * h / 2, k2v = A(gm[j], x0 + k1x * h / 2, k2x);
      const k3x = u0 + k2v * h / 2, k3v = A(gm[j], x0 + k2x * h / 2, k3x);
      const k4x = u0 + k3v * h, k4v = A(ge[j], x0 + k3x * h, k4x);
      x[j] = x0 + (k1x + 2 * k2x + 2 * k3x + k4x) * h / 6; v[j] = u0 + (k1v + 2 * k2v + 2 * k3v + k4v) * h / 6;
    }
    ga = ge;
  }
  if (x.some(q => !isFinite(q))) throw new Error('follow 算出了非有限数：检查 leader 是否返回了 NaN 或非数字的数组元素');
  const out = vec ? x : x[0]; byL.set(key, out); return vec ? out.slice() : out;
}
// 入场落在拍上。spring(t - tb) 在 tb 那一帧恰好是 0，riseLine / slamLine 在 lt<=0 时不画，所以「第 N 拍开始入场」的那一拍是空画面。
// enter 返回从 tb - lead 起算的局部时间（用法：riseLine(ctx, s, x, y, enter(t, b(8)))），拍点那一帧已经能看到入场的第一步。
const enter = (t, tb, lead = 0.05) => t - (tb - lead);
// 「拍子是落点」：动作在 tb - dur 开始，tb 那一帧恰好到位，返回 0..1（用法：x = lerp(x0, x1, land(t, b(8), 0.3))）。
// ease 要是 0..1 归一的缓动（E.out3、E.outBack）；spring 没有固定终点时间，不适用。
const land = (t, tb, dur = 0.25, ease = E.out3) => ease(prog(t, tb - dur, dur));
// 从 t0 起按 tau 秒指数衰减，t0 之前是 0。不要直接写 Math.exp(-(t - t0) / tau)：t < t0 时它会变成几十、几百倍，
// 在镜头的 pre 重叠段里把元素放大或拉成怪形。
const decay = (t, t0, tau) => t < t0 ? 0 : Math.exp(-(t - t0) / tau);
const inout = (t, a, dur, b = 1e9, dur2 = 0.5) => E.out3(prog(t, a, dur)) * (1 - E.in3(prog(t, b, dur2)));
// ---------------------------------------------------------------- stagger：一组元素按先后落位
// 纯函数：只由参数算出，不存状态。返回长度 n 的数组，每项是第 i 个元素的局部时间（秒，未开始时为负）；给了 o.dur 就返回 0..1 的进度。
//   stagger(t, n, gap, o)   t = 已减去起点的时间（常写 t - S.t0 或 enter(t, b(8))），gap = 相邻两个元素的间隔秒数
//   o.order：'index'（默认，0 先动）| 'reverse'（最后一个先动）| 'center'（从中间向两边）| 'edges'（从两边向中间）
//            | 'point'（按到 o.from 的距离，近的先动；o.pos = [[x, y], ...] 每个元素的位置）| 'random'（按 o.seed 打乱）
//   o.dur：给了就返回进度 ease(clamp(局部时间 / dur))；o.ease 默认 E.out3
//   n = 0 返回空数组；gap = 0 时全部同时开始；gap < 0 报错（要倒序用 'reverse'）。
//   'point' 的间隔按距离等比换算：最远的元素晚 (n - 1) * gap 开始，总时长和 'index' 相同。
//   例：const p = stagger(t - S.t0, cards.length, 0.06, { order: 'center', dur: 0.4 }); cards.forEach((c, i) => drawCard(c, lerp(80, 0, p[i])));
//   例：const lt = stagger(lt0, n, 0.03); 第 i 个元素用 spring(lt[i]) —— 与 spring(lt0 - i * 0.03) 完全相同。
function staggerDelays(n, gap, o = {}) {
  if (!Number.isInteger(n) || n < 0) throw new Error('stagger 的 n（元素个数）要是 ≥ 0 的整数，收到 ' + n);
  if (typeof gap !== 'number' || !isFinite(gap) || gap < 0) throw new Error('stagger 的 gap 要是 ≥ 0 的秒数，收到 ' + gap + '；想让后面的先动，用 o.order = \'reverse\'');
  const order = o.order || 'index', d = new Array(n);
  if (order === 'index') for (let i = 0; i < n; i++) d[i] = i * gap;
  else if (order === 'reverse') for (let i = 0; i < n; i++) d[i] = (n - 1 - i) * gap;
  else if (order === 'center' || order === 'edges') {
    const c = (n - 1) / 2;
    for (let i = 0; i < n; i++) { const k = Math.abs(i - c); d[i] = (order === 'center' ? k : c - k) * gap; }
  } else if (order === 'point') {
    const pos = o.pos, from = o.from; if (!pos || pos.length < n || !from) throw new Error("stagger order 'point' 需要 o.pos（每个元素的 [x, y]）和 o.from（[x, y]）");
    const ds = []; for (let i = 0; i < n; i++) ds.push(Math.hypot(pos[i][0] - from[0], pos[i][1] - from[1]));
    const lo = Math.min(...ds), hi = Math.max(...ds), span = hi - lo || 1;
    for (let i = 0; i < n; i++) d[i] = (ds[i] - lo) / span * (n - 1) * gap;
  } else if (order === 'random') {
    const r = rng(o.seed ?? 1), idx = []; for (let i = 0; i < n; i++) idx.push(i);
    for (let i = n - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
    for (let k = 0; k < n; k++) d[idx[k]] = k * gap;
  } else throw new Error('stagger 不认识的 order：' + order + "（可用 index、reverse、center、edges、point、random）");
  return d;
}
function stagger(t, n, gap, o = {}) {
  const d = staggerDelays(n, gap, o), out = new Array(n), ease = o.ease || E.out3;
  for (let i = 0; i < n; i++) { const lt = t - d[i]; out[i] = o.dur ? ease(clamp(lt / o.dur)) : lt; }
  return out;
}
function rng(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let x = s; x = Math.imul(x ^ (x >>> 15), x | 1); x ^= x + Math.imul(x ^ (x >>> 7), x | 61); return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; }
// 1D 值噪声（-1..1），做手持感、漂浮、震动
function vnoise(x, seed = 0) {
  const h = n => { const s = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453; return s - Math.floor(s); };
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(h(i), h(i + 1), u) * 2 - 1;
}
// ---------------------------------------------------------------- 颜色：输入任何 CSS 颜色，输出能继续当输入
// parseColor(c) → [r, g, b, a]（r g b 0–255 整数，a 0–1）。直接认 #rgb、#rgba、#rrggbb、#rrggbbaa、rgb()、rgba()（逗号或空格分隔，
//   alpha 可写 / 0.5 或百分比）；其他 CSS 写法（hsl()、red 这类颜色名）交给浏览器换算。认不出时抛出说明。结果按字符串缓存。
// hexA(c, a)：c 的透明度乘以 a，返回 rgba()。mixHex(c1, c2, u)：按 u 混合（0 = c1，1 = c2），不透明时返回 #rrggbb，否则 rgba()。
// 例：ctx.fillStyle = hexA(mixHex(COL.dim, COL.acc, u), 0.8);
const _PC = new Map();
function parseColor(c) {
  if (Array.isArray(c) && c.length >= 3) return [c[0], c[1], c[2], c[3] ?? 1];
  if (typeof c !== 'string') throw new Error('颜色要写成字符串（#rrggbb、rgb(…)、rgba(…) 等），收到的是 ' + _fshow(c));
  const hit = _PC.get(c); if (hit) return hit;
  const s = c.trim().toLowerCase(); let out = null, m;
  if ((m = /^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/.exec(s))) {
    let h = m[1]; if (h.length <= 4) h = [...h].map(x => x + x).join('');
    out = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)).concat(h.length === 8 ? Math.round(parseInt(h.slice(6), 16) / 255 * 1000) / 1000 : 1);
  } else if ((m = /^rgba?\(([^)]*)\)$/.exec(s))) {
    const p = m[1].split(/[\s,\/]+/).filter(Boolean), num = (v, k) => { const x = parseFloat(v); return v.endsWith('%') ? x * k / 100 : x; };
    if (p.length === 3 || p.length === 4) {
      out = [0, 1, 2].map(i => Math.round(clamp(num(p[i], 255), 0, 255))).concat(p.length === 4 ? clamp(num(p[3], 1)) : 1);
      if (out.some(v => !isFinite(v))) out = null;
    }
  } else if (s) {                                                  // hsl()、颜色名：让浏览器换算成 #rrggbb 或 rgba()
    _M.fillStyle = '#010203'; _M.fillStyle = s; const a = _M.fillStyle;
    _M.fillStyle = '#040506'; _M.fillStyle = s; const b2 = _M.fillStyle;
    if (a === b2) out = parseColor(a);
  }
  if (!out) throw new Error(`认不出的颜色：${_fshow(c)}。写成 #rrggbb、#rgb、#rrggbbaa、rgb(r, g, b) 或 rgba(r, g, b, a)`);
  if (_PC.size > 2000) _PC.clear(); _PC.set(c, out); return out;
}
const _hex2 = v => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, '0');
function _colorOut(r, g, b, a) { return a >= 1 ? '#' + _hex2(r) + _hex2(g) + _hex2(b) : `rgba(${Math.round(clamp(r, 0, 255))},${Math.round(clamp(g, 0, 255))},${Math.round(clamp(b, 0, 255))},${Math.round(clamp(a) * 1000) / 1000})`; }
function hexA(c, a) { const [r, g, b, a0] = parseColor(c); return `rgba(${r},${g},${b},${Math.round(clamp(a0 * a) * 1000) / 1000})`; }
function mixHex(c1, c2, u) { const A = parseColor(c1), B = parseColor(c2); return _colorOut(lerp(A[0], B[0], u), lerp(A[1], B[1], u), lerp(A[2], B[2], u), clamp(lerp(A[3], B[3], u))); }

// ---------------------------------------------------------------- 时间轴与节拍（timeline.json 由 tools/timeline.py 生成，所有模式都有 bpm）
const TL = window.TL;
const BPM = TL.bpm || 120, BEAT = 60 / BPM, BAR = BEAT * 4, OFFSET = TL.offset || 0;
const b = n => OFFSET + n * BEAT;               // 第 n 拍的时刻（秒）；OFFSET 是用户歌曲第一拍的位置
const beatOf = t => (t - OFFSET) / BEAT;
const SCN = id => TL.scenes[id];
const ph = (id, k) => { const p = TL.scenes[id].phrases; return p[Math.min(k, p.length - 1)].t0; };   // 配音模式：第 k 个短句开始
const phE = (id, k) => { const p = TL.scenes[id].phrases; return p[Math.min(k, p.length - 1)].t1; };
// 片型：project.json 的 genre，没写时配音模式算讲解片，其余算宣传片（和 tools/layout.py 的判断相同）
const GENRE = PROJECT.genre || (TL.mode === 'voice' ? 'explainer' : 'promo');

// ---------------------------------------------------------------- act：画面事件，一个短句对应画面上的一个动作
// act(t, at, o) 返回 0..1：从 at - o.lead 开始、按 o.ease（默认 E.out3）走完 o.dur 秒的进度。at 常写 ph('S05', 2) 或 b(8)。
//   o.dur 默认：讲解片取 at 所在短句时长的 40%，限制在 0.4–1.2 秒（at 不在某个短句开头 ±0.05 秒内时取 0.6 秒）；宣传片取 1 拍。
//   o.name 事件名（体检的对齐图上显示）；o.lead 提前起手的秒数（默认 0）。
//   每次调用往 window.__ACTS 推 {name, at, dur, shot, lead}（同一帧里相同的只记一次），main.js 每帧清空；体检据此画「短句 ↔ 画面事件」对齐图。
// 例：const u = act(t, ph('S03', 1), { name: '水柱上升' }); column(ctx, u);
window.__ACTS = [];
let _PHR = null;
function _phraseAt(at) {
  if (!_PHR) _PHR = Object.values(TL.scenes).flatMap(s => s.phrases || []).filter(p => isFinite(p.t0) && isFinite(p.t1)).sort((x, y) => x.t0 - y.t0);
  let lo = 0, hi = _PHR.length - 1, best = null;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (_PHR[m].t0 < at) lo = m + 1; else hi = m - 1; }
  for (const i of [lo - 1, lo]) { const p = _PHR[i]; if (p && Math.abs(p.t0 - at) <= 0.05 && (!best || Math.abs(p.t0 - at) < Math.abs(best.t0 - at))) best = p; }
  return best;
}
function actDur(at) {
  if (GENRE !== 'explainer') return BEAT;
  const p = _phraseAt(at); return p ? clamp(0.4 * (p.t1 - p.t0), 0.4, 1.2) : 0.6;
}
function act(t, at, o = {}) {
  if (typeof at !== 'number' || !isFinite(at)) throw new Error("act 的 at 要是秒数（常写 ph('S05', 2) 或 b(8)），收到的是 " + _fshow(at));
  const lead = o.lead ?? 0, dur = o.dur ?? actDur(at), st = at - lead, name = o.name ?? null, shot = SHOT_NOW ?? null;
  const A = window.__ACTS, r4 = v => Math.round(v * 1e4) / 1e4;
  if (!A.some(a => a.at === r4(at) && a.name === name && a.shot === shot)) A.push({ name, at: r4(at), dur: r4(dur), shot, lead });
  if (!(dur > 0)) return t >= st ? 1 : 0;
  return (o.ease || E.out3)(prog(t, st, dur));
}
// 底鼓包络：PROJECT.music.kicks = [[起拍, 止拍), ...]，画面的呼吸（缩放、光晕）与之同步
const KICKS = (() => { const k = []; for (const [a, c, step = 1] of ((PROJECT.music || {}).kicks || [])) for (let i = a; i < c; i += step) k.push(i); return k.sort((x, y) => x - y); })();
function kickEnv(t, tau = 0.14) {
  const bt = beatOf(t); let best = null;
  for (const k of KICKS) { if (k <= bt + 1e-6) best = k; else break; }
  return best === null ? 0 : Math.exp(-(t - b(best)) / tau);
}

// ---------------------------------------------------------------- 音效登记：在画面动作发生的那一刻登记，tools/dump_events.py 导出
window.EVENTS = [];
function EV(t, type, o = {}) { if (isFinite(t)) EVENTS.push(Object.assign({ t: +t.toFixed(4), type }, o)); }

// ---------------------------------------------------------------- 全局效果登记（在镜头文件顶层调用）
const SHAKES = [];   // [t0, 幅度 px, 衰减秒]
// [t0, 强度 0..1, 衰减秒, 颜色, 模式]。模式默认 'light'：overlay 混合，只提亮画面里已有的内容，黑底保持黑，主体在那一下变亮；
// 'add'：整帧加白（真正的闪白帧），会把黑底抬成灰，只用于 1–2 帧的硬闪（衰减 ≤ 0.03 秒）。
// 闪光不能代替内容：drop 那一帧要已经看得到主体。review.py 会报「整帧被刷灰/刷白」的帧。
const FLASH = [];
const CUTS = [];     // 额外的硬切时刻（运动模糊的子帧不跨过它）
const FAST = [];     // [t0, t1, 子帧数]：高速段加密运动模糊
// 镜头的运动标签：project.json 的 timeline.shots[i].motion，"稳"（默认）或 "可以震"。SHAKES 登记在「稳」镜头里的震动不生效。
function shakeOK(t0) { for (const S of Object.values(TL.scenes)) if (t0 >= S.t0 - 1e-6 && t0 < S.t1) return S.motion === '可以震'; return false; }
function shake(t) {
  let x = 0, y = 0, r = 0;
  for (const [t0, amp, tau] of SHAKES) {
    const lt = t - t0; if (lt < 0 || lt > tau * 6) continue;
    if (!shakeOK(t0)) continue;                          // 只有 project.json 里标了 motion: "可以震" 的镜头才会震
    const e = Math.exp(-lt / tau) * amp * U;
    x += vnoise(lt * 38, t0 * 7) * e; y += vnoise(lt * 41, t0 * 7 + 3) * e; r += vnoise(lt * 30, t0 * 7 + 9) * e * 0.0009;
  }
  return [x, y, r];
}
function flashAt(t) {
  let a = 0, col = '#FFFFFF', mode = 'light';
  for (const [t0, s, tau, c, m] of FLASH) { const lt = t - t0; if (lt < 0 || lt > tau * 6) continue; const v = s * Math.exp(-lt / tau); if (v > a) { a = v; col = c || '#FFFFFF'; mode = m || 'light'; } }
  return [a, col, mode];
}

// ---------------------------------------------------------------- 镜头矩阵
// BASE 是这一帧的全局矩阵（震动、底鼓缩放、镜头间转场位移），由 main.js 每帧设置。
// 镜头里只用 screen() 和 cam() 设变换，不要 setTransform(1,0,0,1,0,0)：那会丢掉 BASE，转场和震动就失效了。
// 镜头矩阵登记（体检的抖动检查只看矩阵，不看像素）：cam() 把它设的变换（相对 screen(ctx)，不含 BASE）记进
// window.__CAMS[镜头id] = [a, b, c, d, e, f]，同一镜头以最后一次调用为准；main.js 每帧清空，并记 window.__GLOBAL（震动和底鼓缩放）
// 和 window.__FRAME = {t, shots, base}（base[镜头id] 是这个镜头这一帧的 BASE，含转场位移）。画面上的变换 = base[id] × __CAMS[id]。
let BASE = new DOMMatrix();
window.__CAMS = {};
function screen(ctx) { ctx.setTransform(BASE); }
function cam(ctx, cx = W / 2, cy = H / 2, z = 1, rot = 0) {
  ctx.setTransform(BASE); ctx.translate(W / 2, H / 2); if (rot) ctx.rotate(rot); ctx.scale(z, z); ctx.translate(-cx, -cy);
  const c = Math.cos(rot) * z, s = Math.sin(rot) * z;
  window.__CAMS[SHOT_NOW ?? '_'] = [c, s, -s, c, W / 2 - c * cx + s * cy, H / 2 - s * cx - c * cy];
}
// 关键帧镜头：keys = [[t, cx, cy, z, rot?], ...]；缩放按对数插值，推拉速度更自然
function camKeys(keys, t, ease = E.inOut3) {
  if (t <= keys[0][0]) return keys[0].slice(1);
  for (let i = 1; i < keys.length; i++) if (t < keys[i][0]) {
    const A = keys[i - 1], B = keys[i], u = ease((t - A[0]) / (B[0] - A[0]));
    return A.slice(1).map((v, j) => j === 2 ? Math.exp(lerp(Math.log(v), Math.log(B[j + 1]), u)) : lerp(v, B[j + 1] ?? v, u));
  }
  return keys[keys.length - 1].slice(1);
}
// 手持感的镜头漂移。循环片传 period（一圈的秒数）：改用整数圈的正弦叠加，t 和 t + period 完全相同，首尾不会错开亚像素。
function handheld(t, amp = 6, seed = 1, period = 0) {
  if (!period) return [vnoise(t * 0.7, seed) * amp * U, vnoise(t * 0.6, seed + 5) * amp * U];
  const w = 2 * Math.PI / period, r = rng(seed), n = Math.max(1, Math.round(period * 0.6));
  const f = (ph1, ph2) => (Math.sin(w * n * t + ph1) * 0.6 + Math.sin(w * (n * 2 + 1) * t + ph2) * 0.4) * amp * U;
  return [f(r() * 6.3, r() * 6.3), f(r() * 6.3, r() * 6.3)];
}

// ---------------------------------------------------------------- 持续运动：慢、顺、不抖，不把字推出画面
// SAFE：标题安全区边距（短边的比例）。版面上所有字都放在安全区里；drift 保证镜头推近、漂移后安全区里的东西仍留在画面内（至少留半个边距）。
const SAFE = 0.05;
// 字幕层（project.json 的 subtitles，见「字幕层」一节）开着时，安全区底部的一条留给字幕：SUBS.band 是这条带（画布像素 {x, y, w, h}），
// 默认占安全区高度的 12%（两种语言 18%，subtitles.band 可改）。safeBox() 的底边上移到字幕带的上沿，镜头用 safeBox() 分区就自动避开字幕；
// 关字幕时 safeBox() 和不开字幕层完全一样。
const SUBS = (() => {
  const c = PROJECT.subtitles, off = { on: false, langs: [], size: 'auto', style: 'shadow', band: null };
  if (!c || !c.burn) return off;
  const langs = Array.isArray(c.langs) && c.langs.length ? c.langs.map(String) : ['zh'], style = c.style || 'shadow', size = c.size ?? 'auto';
  const bad = [];
  if (TL.mode !== 'voice') bad.push('字幕按配音短句画，只用于配音驱动的时间轴（timeline.mode = "voice"）；没有配音的片子不开 subtitles');
  if (langs.length > 2) bad.push(`subtitles.langs 最多两种语言（一行一种），现在是 ${JSON.stringify(langs)}`);
  if (style !== 'shadow' && style !== 'bar') bad.push(`subtitles.style 要是 "shadow"（默认，字带一圈底色光晕）或 "bar"（半透明底条），现在是 ${JSON.stringify(style)}`);
  if (size !== 'auto' && !(size > 0)) bad.push(`subtitles.size 要是 "auto" 或数字（1080p 下第一行的字号 px，按短边换算），现在是 ${JSON.stringify(size)}`);
  if (bad.length) { const m = 'project.json 的 subtitles：' + bad.join('；'); window.__FATAL = m; throw new Error(m); }
  const sh = H * (1 - 2 * SAFE), bh = sh * clamp(c.band ?? (langs.length > 1 ? 0.18 : 0.12), 0.05, 0.4);
  return { on: true, langs, size, style, band: _R(W * SAFE, H * SAFE + sh - bh, W * (1 - 2 * SAFE), bh) };
})();
const safeBox = () => SUBS.on ? _R(W * SAFE, H * SAFE, W * (1 - 2 * SAFE), SUBS.band.y - H * SAFE) : _R(W * SAFE, H * SAFE, W * (1 - 2 * SAFE), H * (1 - 2 * SAFE));
// ---------------------------------------------------------------- 版面：分区与等比放置（纯函数，只用传入的矩形和 W、H、U 计算）
// 矩形都同时带两种写法 {x, y, w, h, x0, y0, x1, y1}，可以直接交给 chartScale 的 box；参数里的矩形写哪一种都行。
// 先把画面分区，再把物件按自然尺寸放进分到的区域：位置和缩放都由区域算出，横版、竖版、方形用同一套代码。
//   split(box, dir, parts, gap)  dir 'row' 左到右、'col' 上到下；parts 权重数组（[2, 1] = 三分之二和三分之一）或份数；返回矩形数组
//   grid(box, cols, rows, gap)   按行优先返回 cols × rows 个矩形；gap 是数或 [横向, 纵向]
//   inset(box, m)                四边各收 m；m 可以是 [上, 右, 下, 左] 或 [上下, 左右]，负数是外扩
//   fit(box, w, h, o)            把自然尺寸 w × h 的物体等比放进 box，返回 {x, y, w, h, s}（s 是缩放倍数）；
//                                o.fill 0–1 占 box 的比例（默认 1）；o.align 'center'（默认）| 'top' | 'bottom' | 'left' | 'right'，可组合 'top left'
// 例：const [stage, side] = split(inset(safeBox(), 20 * U), PORTRAIT ? 'col' : 'row', [3, 2], 40 * U);
//     const f = fit(stage, 600, 420, { align: 'bottom' });
//     ctx.save(); ctx.translate(f.x, f.y); ctx.scale(f.s, f.s); drawShop(ctx, t); ctx.restore();   // drawShop 按 600 × 420 的自然尺寸画
function _R(x, y, w, h) { return { x, y, w, h, x0: x, y0: y, x1: x + w, y1: y + h }; }
function _bx(b) {
  if (!b || typeof b !== 'object') throw new Error('版面函数的矩形要写成 {x, y, w, h} 或 {x0, y0, x1, y1}，收到的是 ' + _fshow(b));
  if (b.w !== undefined && b.x !== undefined) return b;
  if (b.x0 !== undefined) return _R(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0);
  throw new Error('版面函数的矩形要写成 {x, y, w, h} 或 {x0, y0, x1, y1}，收到的是 ' + JSON.stringify(b));
}
function split(box, dir, parts, gap = 0) {
  const B = _bx(box), P = typeof parts === 'number' ? new Array(Math.max(1, parts | 0)).fill(1) : parts;
  if (dir !== 'row' && dir !== 'col') throw new Error("split 的 dir 要是 'row'（左到右）或 'col'（上到下），收到的是 " + _fshow(dir));
  if (!Array.isArray(P) || !P.length || P.some(w => !(w >= 0))) throw new Error('split 的 parts 要是非负权重数组（如 [2, 1]）或份数，收到的是 ' + _fshow(parts));
  const row = dir === 'row', len = (row ? B.w : B.h) - gap * (P.length - 1), sum = P.reduce((a, c) => a + c, 0) || 1, out = [];
  let p = row ? B.x : B.y;
  for (const w of P) { const d = len * w / sum; out.push(row ? _R(p, B.y, d, B.h) : _R(B.x, p, B.w, d)); p += d + gap; }
  return out;
}
function grid(box, cols, rows, gap = 0) {
  const B = _bx(box), [gx, gy] = Array.isArray(gap) ? gap : [gap, gap], cw = (B.w - gx * (cols - 1)) / cols, rh = (B.h - gy * (rows - 1)) / rows, out = [];
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) out.push(_R(B.x + i * (cw + gx), B.y + j * (rh + gy), cw, rh));
  return out;
}
function inset(box, m) {
  const B = _bx(box), [t, r, b, l] = Array.isArray(m) ? (m.length === 2 ? [m[0], m[1], m[0], m[1]] : m) : [m, m, m, m];
  return _R(B.x + l, B.y + t, B.w - l - r, B.h - t - b);
}
function fit(box, w, h, o = {}) {
  const B = _bx(box); if (!(w > 0 && h > 0)) throw new Error(`fit 的自然尺寸要是正数，收到的是 ${w} × ${h}`);
  const s = Math.min(B.w / w, B.h / h) * (o.fill ?? 1), fw = w * s, fh = h * s, a = o.align || 'center';
  const x = /left/.test(a) ? B.x : /right/.test(a) ? B.x + B.w - fw : B.x + (B.w - fw) / 2;
  const y = /top/.test(a) ? B.y : /bottom/.test(a) ? B.y + B.h - fh : B.y + (B.h - fh) / 2;
  return Object.assign(_R(x, y, fw, fh), { s });
}
// ---------------------------------------------------------------- 物件表：主角物件按自然尺寸写成一个函数，先单独检查，再放进镜头
// 主角物件（树、猫、相机、太阳）画得潦草，常见的原因是在镜头里边排版边画：腿没接上、被画框切掉、压到字。做法是把它登记进 PROP，
// 按自然尺寸画（原点在左上角，坐标范围 0..size），tools/stills.py --props 把全部物件按大尺寸、几个时刻画成一张物件表，检查部件相接、
// 比例、线宽和轮廓后再进镜头。镜头里用 prop() 放进分区，位置和缩放由分区算出，物件自然占满分到的区域。
//   PROP.名字 = function (ctx, t, o) {...}   t 是时间（物件自己的动作用它算），o 是 prop() 收到的选项（可以带物件自己的参数，如 o.mood）
//   PROP.名字.size = [宽, 高]                 自然尺寸，必填
//   prop(ctx, name, box, o)                   = fit(box, ...size, o) 后平移缩放再调用 PROP.名字(ctx, o.t ?? 当前时刻, o)；返回 fit 的结果 {x, y, w, h, s}
//                                             o.fill、o.align 同 fit；物件里用 anchor() 登记的锚点自动换算到画布上
//   window.__PROPS = [{name, size}]           引擎启动后登记的全部物件（stills.py --props 读它）
// 例：PROP.cat = function (ctx, t, o) { ctx.fillStyle = COL.ink; ctx.beginPath(); ctx.ellipse(300, 300, 220, 160, 0, 0, Math.PI * 2); ctx.fill(); };
//     PROP.cat.size = [600, 480];
//     SHOT.S02 = function (ctx, t, S) { screen(ctx); const f = prop(ctx, 'cat', STAGE, { align: 'bottom' }); };
const PROP = window.PROP = window.PROP || {};
let T_NOW = 0;                                          // 当前这一帧（子帧）的时刻，由 main.js 设置；prop() 默认把它传给物件
function _propSize(name) {
  const P = PROP[name];
  if (typeof P !== 'function') throw new Error(`prop：没有登记物件「${name}」。先写 PROP.${name} = function (ctx, t, o) {...} 和 PROP.${name}.size = [宽, 高]` + (Object.keys(PROP).length ? `（已登记：${Object.keys(PROP).join('、')}）` : ''));
  const s = P.size;
  if (!Array.isArray(s) || s.length !== 2 || !(s[0] > 0 && s[1] > 0)) throw new Error(`PROP.${name}.size 缺失或写错（收到 ${_fshow(s)}）：写 PROP.${name}.size = [宽, 高]，是画这个物件时用的自然尺寸，prop() 按它把物件放进分区`);
  return s;
}
function prop(ctx, name, box, o = {}) {
  const [w, h] = _propSize(name), f = fit(box, w, h, o);
  ctx.save(); ctx.translate(f.x, f.y); ctx.scale(f.s, f.s);
  try { PROP[name](ctx, o.t ?? T_NOW, o); } finally { ctx.restore(); }
  return f;
}
// drift(t, S, o)：镜头整段缓推 + 一道慢弧线漂移，返回 [cx, cy, z]，交给 cam(ctx, ...drift(t, S))。
//   整个镜头里速度只换一次方向，没有来回小抖。o.push 推近比例（默认 0.04），o.amp 漂移幅度 px（默认 12），o.seed。
//   推近和漂移会被自动收紧，保证安全区内容不出画面。
function drift(t, S, o = {}) {
  const u = E.inOut2(clamp((t - S.t0) / Math.max(0.1, S.t1 - S.t0))), r = rng(o.seed ?? 3), ph = r() * 6.283, ph2 = r() * 6.283;
  const zMax = (0.5 - SAFE / 2) / (0.5 - SAFE);
  const z = Math.min(1 + (o.push ?? 0.04) * u, zMax);
  const lim = d => Math.max(0, d * ((0.5 - SAFE / 2) / z - (0.5 - SAFE)));   // 这一轴还能漂多少 px
  const a = (o.amp ?? 12) * U;
  const dx = clamp(a * Math.sin(Math.PI * u + ph), -lim(W), lim(W)), dy = clamp(a * 0.6 * Math.sin(Math.PI * u + ph2), -lim(H), lim(H));
  return [W / 2 + dx, H / 2 + dy, z];
}
// idle(t, i, o)：次要元素的持续小动作（慢浮动、呼吸），第 i 个元素相位不同。返回 {x, y, s, r}。
//   单一低频正弦，周期默认 4 秒（不短于 2.5 秒），幅度默认 6px：看得出在动，但不抖。不要用在正文文字上。
function idle(t, i = 0, o = {}) {
  const per = Math.max(2.5, o.period ?? 4), ph = rng(1000 + i)() * 6.283, w = 2 * Math.PI / per, a = (o.amp ?? 6) * U;
  return { x: Math.cos(w * t + ph) * a * 0.5, y: Math.sin(w * t + ph) * a, s: 1 + Math.sin(w * t + ph * 1.3) * (o.breathe ?? 0.015), r: 0 };
}
// chartScale(o)：图表的唯一一套「数据 → 像素」映射。折线、柱子、数值标签、箭头都从同一个数据数组和这一个 scale 算位置，数字和画面才对得上。
//   o = {data, box: {x0, y0, x1, y1}, min, max, pad}；返回 {x(i), y(v), bar(i, w), base, data, box, min, max}。x(i) 的 i 可以是小数（两个数据点之间）。
//   例：const C = chartScale({ data: [124, 168, 132, 150], box: { x0: 300, y0: 260, x1: 1500, y1: 820 }, min: 0 });
//       柱顶 C.y(v)，标签画在 C.y(v) - 12，折线点 [C.x(i), C.y(v)]；要标某个数值用 pin(ctx, C, v, {...})，指向数据点用 anchor + callout。
function chartScale(o) {
  const d = o.data, n = d.length, B = o.box, lo = o.min ?? Math.min(...d), hi = o.max ?? Math.max(...d), pad = o.pad ?? 0.5;
  const x = i => B.x0 + (B.x1 - B.x0) * (i + pad) / (n - 1 + 2 * pad);
  const y = v => B.y1 - (B.y1 - B.y0) * (v - lo) / ((hi - lo) || 1);
  return { x, y, base: y(lo), data: d, box: B, min: lo, max: hi, bar: (i, w) => ({ x: x(i) - w / 2, y: y(d[i]), w, h: y(lo) - y(d[i]) }) };
}

// ---------------------------------------------------------------- 锚点与标注：引线、图钉的终点从目标的几何算出来
// 手填坐标的引线，目标一动就脱节：指到背景、落错位置、几条线交叉。做法是画目标时用 anchor 登记它占的区域，
// 标注用 callout 指向这个名字，终点由引擎从锚点算出；镜头推拉、转场位移、震动都会自动跟上，体检也能逐帧核对。
//   anchor(ctx, name, x, y, w, h)
//       在当前变换下（cam、screen、translate 之后都行）登记目标区域，换算成画布像素存进 window.__ANCHORS[name] = {x, y, w, h}，
//       返回这个矩形。有旋转时取四个角的外接矩形。同名的后登记覆盖先登记的。
//   callout(ctx, target, from, o)
//       从 from 画引线到锚点 target 的边缘（离起点最近的点），返回 {from, end, pts}（画布像素），没画时返回 null。
//       from：[x, y] 是 screen(ctx) 下的版面坐标（不含 cam；转场位移和震动自动带上），或另一个锚点名（从那个锚点朝向目标的一边出发，
//             标签也用 anchor 登记，就能写 callout(ctx, '目标', '目标的标签')）。
//       o.p 生长进度 0..1（默认 1，用 land()/prog() 算）；o.elbow 'h' 先横后竖、'v' 先竖后横（默认直线）；o.aim [u, v] 改为瞄准目标里的
//       相对位置（0..1，例如 [0.5, 0.5] 指向中心），终点是起点到该点的连线与目标边缘的交点；o.dot 终点圆点半径（默认 4U，0 不画）；
//       o.arrow 箭头大小（给了就不画圆点）；o.color（默认 COL.ink）、o.lw（默认 2U）、o.alpha、o.dash。
//       每次画出时往 window.__LINKS 推一条 {to, from: [x, y], end: [x, y], shot, p}（shot 是当前镜头 id），体检据此检查终点是否落在目标上。
//       目标这一帧没有登记（还没画、名字写错、anchor 写在了 callout 之后）时不画，控制台警告一次。
//   pin(ctx, C, value, o)
//       在 chartScale 的图上按数值放标记，位置由 C 算出，和图表本身在同一个变换下画，返回 {x, y}（当前坐标）。
//       给 o.at（第几个数据点，可以是小数）：图钉立在数据点 [C.x(at), C.y(value)] 上（标峰值、标某一年）；
//       不给 o.at：在 y 轴的 C.y(value) 处画刻度和横贯图区的参考虚线（标平均值、阈值）。
//       o.label 标签；o.p 进度 0..1；o.name 同时登记成锚点（callout 可以指向它）；o.color（默认 COL.acc）、o.font、
//       o.len 图钉高度（默认 48U）、o.r 钉头半径（默认 7U）、o.side 参考线标签放在 'right'（默认）或 'left'。
// 一帧之内先 anchor 后 callout。main.js 每帧绘制前清空 __ANCHORS 和 __LINKS，所以表里只有这一帧画出来的东西。
// 例：
//   cam(ctx, ...camKeys(KEYS, t));                                   // 镜头在推近，目标跟着动
//   ctx.fillStyle = COL.acc; rrect(ctx, 820, 400, 160, 90, 12); ctx.fill(); anchor(ctx, 'valve', 820, 400, 160, 90);
//   screen(ctx); txt(ctx, '阀门', 300, 236, { font: F.b(40) }); anchor(ctx, 'valve.label', 300, 200, measure('阀门', F.b(40)), 48);
//   callout(ctx, 'valve', 'valve.label', { elbow: 'h', p: land(t, ph('S02', 1) + 0.4, 0.4) });
//   const C = chartScale({ data: [3, 7, 5, 9], box: { x0: 300, y0: 600, x1: 900, y1: 900 }, min: 0 });
//   pin(ctx, C, 9, { at: 3, label: '最高 9', p: prog(t, ph('S03', 2), 0.5) });
let SHOT_NOW = null;                                    // 当前正在画的镜头 id，由 main.js 设置
window.__ANCHORS = {}; window.__LINKS = [];
const _CW = new Set();
function anchor(ctx, name, x, y, w, h) {
  const m = ctx.getTransform(), P = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].map(([px, py]) => [m.a * px + m.c * py + m.e, m.b * px + m.d * py + m.f]);
  const xs = P.map(p => p[0]), ys = P.map(p => p[1]), x0 = Math.min(...xs), y0 = Math.min(...ys);
  const r = { x: x0, y: y0, w: Math.max(...xs) - x0, h: Math.max(...ys) - y0 };
  window.__ANCHORS[name] = r; return r;
}
function _anchorGet(name) {
  const r = window.__ANCHORS[name];
  if (!r && !_CW.has(name)) { _CW.add(name); console.warn(`callout：这一帧没有锚点「${name}」（还没画、名字写错，或 anchor 写在了 callout 之后），这条线没有画`); }
  return r || null;
}
// 锚点 r 朝向点 q 的那一边的中点（标签作为起点时用）
function _sideMid(r, q, prefer) {
  const cx = r.x + r.w / 2, cy = r.y + r.h / 2, outX = q[0] < r.x || q[0] > r.x + r.w, outY = q[1] < r.y || q[1] > r.y + r.h;
  const horiz = prefer === 'v' ? !outY && outX : outX || !outY;
  return horiz ? [q[0] < cx ? r.x : r.x + r.w, cy] : [cx, q[1] < cy ? r.y : r.y + r.h];
}
// 起点 s 到矩形 r 的终点和折线
function _calloutPts(s, r, o) {
  const [sx, sy] = s, x1 = r.x + r.w, y1 = r.y + r.h, inX = sx >= r.x && sx <= x1, inY = sy >= r.y && sy <= y1;
  if (o.elbow === 'h' && !inY) { const ex = r.x + r.w * (o.aim ? o.aim[0] : 0.5), ey = sy < r.y ? r.y : y1; return [s, [ex, sy], [ex, ey]]; }
  if (o.elbow === 'v' && !inX) { const ey = r.y + r.h * (o.aim ? o.aim[1] : 0.5), ex = sx < r.x ? r.x : x1; return [s, [sx, ey], [ex, ey]]; }
  if (o.elbow === 'h') return [s, [sx < r.x ? r.x : x1, sy]];
  if (o.elbow === 'v') return [s, [sx, sy < r.y ? r.y : y1]];
  if (o.aim && !(inX && inY)) {                          // 起点到瞄准点的连线进入矩形的那一点（Liang–Barsky 裁剪的入口参数）
    const dx = r.x + r.w * clamp(o.aim[0]) - sx, dy = r.y + r.h * clamp(o.aim[1]) - sy; let u = 0;
    for (const [pp, qq] of [[-dx, sx - r.x], [dx, x1 - sx], [-dy, sy - r.y], [dy, y1 - sy]]) if (pp < 0) u = Math.max(u, qq / pp);
    return [s, [sx + dx * u, sy + dy * u]];
  }
  return [s, [clamp(sx, r.x, x1), clamp(sy, r.y, y1)]];
}
function callout(ctx, target, from, o = {}) {
  const r = _anchorGet(target); if (!r) return null;
  const p = clamp(o.p ?? 1); if (p <= 0) return null;
  const c = { x: r.x + r.w / 2, y: r.y + r.h / 2 };
  let s;
  if (typeof from === 'string') { const fr = _anchorGet(from); if (!fr) return null; s = _sideMid(fr, [c.x, c.y], o.elbow); }
  else { const m = BASE; s = [m.a * from[0] + m.c * from[1] + m.e, m.b * from[0] + m.d * from[1] + m.f]; }
  const pts = _calloutPts(s, r, o), end = pts[pts.length - 1], q = v => Math.round(v * 100) / 100;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);        // 锚点已经是画布像素（含 BASE），这里按像素画
  const col = o.color || COL.ink;
  drawPath(ctx, pts, p, { color: col, lw: o.lw ?? 2 * U, alpha: o.alpha, dash: o.dash, arrow: o.arrow });
  const dr = (o.dot ?? 4) * U * E.outBack(clamp((p - 0.85) / 0.15));
  if (!o.arrow && dr > 0) { ctx.globalAlpha *= (o.alpha ?? 1); ctx.fillStyle = col; ctx.beginPath(); ctx.arc(end[0], end[1], dr, 0, Math.PI * 2); ctx.fill(); }
  ctx.restore();
  window.__LINKS.push({ to: target, from: [q(s[0]), q(s[1])], end: [q(end[0]), q(end[1])], shot: SHOT_NOW ?? null, p: q(p) });
  return { from: s, end, pts };
}
function pin(ctx, C, value, o = {}) {
  const p = clamp(o.p ?? 1); if (p <= 0) return null;
  const B = C.box, y = C.y(value), col = o.color || COL.acc, font = o.font || F.b(28 * U, 600), la = clamp((p - 0.5) / 0.5);
  ctx.save(); ctx.globalAlpha *= (o.alpha ?? 1); ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineCap = 'round';
  if (o.at !== undefined) {
    const x = C.x(o.at), len = (o.len ?? 48) * U, r = (o.r ?? 7) * U, top = y - len * E.out3(clamp(p / 0.6)), hr = r * E.outBack(clamp((p - 0.3) / 0.5));
    ctx.lineWidth = 2 * U; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, top); ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, r * 0.55, 0, Math.PI * 2); ctx.fill();
    if (hr > 0) { ctx.beginPath(); ctx.arc(x, top, hr, 0, Math.PI * 2); ctx.fill(); }
    if (o.label && la > 0) txt(ctx, o.label, x, top - r - 12 * U, { font, color: col, align: 'center', alpha: la });
    if (o.name) anchor(ctx, o.name, x - r, top - r, 2 * r, y - top + 2 * r);
    ctx.restore(); return { x, y };
  }
  const xe = lerp(B.x0, B.x1, E.out3(p));
  ctx.lineWidth = 2 * U; ctx.beginPath(); ctx.moveTo(B.x0 - 12 * U, y); ctx.lineTo(B.x0, y); ctx.stroke();
  ctx.setLineDash([8 * U, 8 * U]); ctx.lineWidth = 1.5 * U; ctx.beginPath(); ctx.moveTo(B.x0, y); ctx.lineTo(xe, y); ctx.stroke(); ctx.setLineDash([]);
  if (o.label && la > 0) { const L = o.side === 'left'; txt(ctx, o.label, L ? B.x0 - 22 * U : B.x1 + 16 * U, y, { font, color: col, align: L ? 'right' : 'left', base: 'middle', alpha: la }); }
  if (o.name) anchor(ctx, o.name, B.x0, y - 3 * U, B.x1 - B.x0, 6 * U);
  ctx.restore(); return { x: B.x0, y };
}

// ---------------------------------------------------------------- 背景
function fillBg(ctx, color = COL.bg) { ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = color; ctx.fillRect(0, 0, W, H); ctx.restore(); }
// 光晕：以 (x, y) 为中心的加亮。半径不要超过主体尺寸的 1.5 倍：铺满全屏的光晕会把黑底抬成灰，主体反而不突出。
function glow(ctx, x, y, r, color, a = 0.25) {
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, color[0] === '#' ? hexA(color, a) : color); g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2); ctx.restore();
}

// ---------------------------------------------------------------- 文字
const _M = document.createElement('canvas').getContext('2d');
function measure(s, font, ls = 0) { _M.font = font; _M.letterSpacing = ls + 'px'; return _M.measureText(s).width; }
const fsize = font => parseFloat(font.match(/([\d.]+)px/)[1]);
function txt(ctx, s, x, y, o = {}) {
  ctx.save(); ctx.font = o.font || F.b(40); ctx.fillStyle = o.color || COL.ink; ctx.globalAlpha *= (o.alpha ?? 1);
  ctx.textAlign = o.align || 'left'; ctx.textBaseline = o.base || 'alphabetic'; ctx.letterSpacing = (o.ls || 0) + 'px';
  ctx.fillText(s, x, y); ctx.restore();
}
// 每个字的 x 偏移（含字距），逐字动画用
function glyphX(s, font, ls = 0) { const xs = [], ch = [...s]; let acc = ''; for (const c of ch) { xs.push(measure(acc, font, ls)); acc += c; } return { xs, w: measure(s, font, ls), ch }; }
// 让一行字不超过 maxW：返回缩小后的字号
function fitSize(s, fontFn, size, maxW, ls = 0) { const w = measure(s, fontFn(size), ls); return w <= maxW ? size : size * maxW / w; }
// 按宽度断行（中英文都可）
function wrap(s, font, maxW, ls = 0) {
  const out = []; let line = '';
  const toks = /[\u3000-\u9fff\uff00-\uffef]/.test(s) ? [...s] : s.split(/(\s+)/);
  for (const tk of toks) { const t2 = line + tk; if (measure(t2.trim(), font, ls) > maxW && line.trim()) { out.push(line.trim()); line = tk.trimStart(); } else line = t2; }
  if (line.trim()) out.push(line.trim()); return out;
}
function colorRange(s, ranges) { const n = [...s].length, a = new Array(n).fill(null); for (const [i0, i1, c] of ranges) for (let i = i0; i < Math.min(n, i1); i++) a[i] = c; return a; }
function _x0(g, x, align) { return align === 'center' ? x - g.w / 2 : align === 'right' ? x - g.w : x; }
// 遮罩内逐字升起。lt = 距出字开始的秒数；o.out 0..1 = 整行向上收走
function riseLine(ctx, s, x, y, lt, o = {}) {
  if (lt <= 0 && !o.static) return 0;
  const font = o.font || F.d(96), size = o.size || fsize(font), ls = o.ls || 0;
  const g = glyphX(s, font, ls), x0 = _x0(g, x, o.align), out = o.out || 0;
  ctx.save(); ctx.font = font; ctx.letterSpacing = ls + 'px'; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  if (o.mask !== false) { ctx.beginPath(); ctx.rect(x0 - size, y - size * 1.05, g.w + size * 2, size * 1.36); ctx.clip(); }
  ctx.globalAlpha *= (o.alpha ?? 1);
  const st = o.stagger ?? 0.02, f = o.f ?? 2.4, z = o.z ?? 0.62, lts = st >= 0 ? stagger(lt, g.ch.length, st) : g.ch.map((_, i) => lt - i * st);  // 负的 o.stagger 沿用旧写法（倒序出字）
  for (let i = 0; i < g.ch.length; i++) {
    const k = o.static ? 1 : spring(lts[i], f, z); if (k <= 0) continue;
    const dy = (1 - k) * size * 1.1 - E.inOut3(clamp(out * 1.4 - i * 0.02 * (out > 0))) * size * 1.3;
    ctx.fillStyle = (o.colors && o.colors[i]) || o.color || COL.ink;
    ctx.fillText(g.ch[i], x0 + g.xs[i], y + dy);
  }
  ctx.restore(); return g.w;
}
// 砸字：每个字从放大透明落到原位（弹簧），用于重拍
function slamLine(ctx, s, x, y, lt, o = {}) {
  if (lt <= 0) return 0;
  const font = o.font || F.d(120), size = o.size || fsize(font), ls = o.ls || 0;
  const g = glyphX(s, font, ls), x0 = _x0(g, x, o.align);
  ctx.save(); ctx.font = font; ctx.letterSpacing = '0px'; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'center';
  const st = o.stagger ?? 0.022, sc0 = o.from ?? 1.6, lts = st >= 0 ? stagger(lt, g.ch.length, st) : g.ch.map((_, i) => lt - i * st);  // 负的 o.stagger 沿用旧写法（倒序出字）
  for (let i = 0; i < g.ch.length; i++) {
    const l = lts[i]; if (l <= 0) continue;
    const k = spring(l, o.f ?? 3.0, o.z ?? 0.5), a = clamp(l / 0.06);
    const cw = (i + 1 < g.ch.length ? g.xs[i + 1] : g.w) - g.xs[i], cx = x0 + g.xs[i] + cw / 2 - ls / 2, cy = y - size * 0.36, sc = lerp(sc0, 1, k);
    ctx.save(); ctx.globalAlpha *= a * (o.alpha ?? 1); ctx.translate(cx, cy); ctx.scale(sc, sc); ctx.translate(0, (1 - k) * -size * 0.25);
    ctx.fillStyle = (o.colors && o.colors[i]) || o.color || COL.ink; ctx.fillText(g.ch[i], 0, size * 0.36); ctx.restore();
  }
  ctx.restore(); return g.w;
}
// 装饰字：刻意做得很小的字（背景水印、纹理里的小字）在 o 里写 deco: true 或 deco: '原因'，体检不按字号下限拦它，
// 但会在报告里逐条列出。txt、riseLine、slamLine 都认（typeOn、rollWords 经由它们也认）；自己直接调 ctx.fillText 的，包一层 deco(ctx, '原因', () => {...})。
// 能读的信息不要标装饰字：观众要读的字就该够大。
function deco(ctx, why, fn) { const p = ctx.__deco; ctx.__deco = why === true || why == null ? '装饰字' : String(why); try { return fn(); } finally { ctx.__deco = p; } }
function _decoWrap(fn, oi) { return function (...a) { const o = a[oi]; return o && o.deco ? deco(a[0], o.deco, () => fn.apply(this, a)) : fn.apply(this, a); }; }
txt = _decoWrap(txt, 4); riseLine = _decoWrap(riseLine, 5); slamLine = _decoWrap(slamLine, 5);
// 同一位置换词：上一个词向上推出，下一个从下方弹起。items = [{s, t, colors?}]
function rollWords(ctx, items, t, x, y, o = {}) {
  let k = -1; for (let i = 0; i < items.length; i++) if (t >= items[i].t) k = i;
  if (k < 0) return 0;
  const cur = items[k], outDur = o.outDur ?? 0.14;
  if (k > 0 && t - cur.t < outDur + 0.02) riseLine(ctx, items[k - 1].s, x, y, 10, Object.assign({}, o, { colors: items[k - 1].colors, out: prog(t, cur.t, outDur), static: true }));
  return riseLine(ctx, cur.s, x, y, t - cur.t, Object.assign({}, o, { colors: cur.colors }));
}
// 打字机：t0 开始每 cps 字/秒；返回已打出的字数（用来登记按键音）
function typeOn(ctx, s, x, y, t, t0, o = {}) {
  const cps = o.cps || 18, n = clamp(Math.floor((t - t0) * cps), 0, [...s].length), shown = [...s].slice(0, n).join('');
  txt(ctx, shown, x, y, o);
  if (o.caret !== false && t >= t0 - 0.3 && (n < [...s].length || Math.floor(t * 2.2) % 2 === 0)) {
    const font = o.font || F.b(40), w = measure(shown, font, o.ls || 0), sz = fsize(font);
    ctx.save(); ctx.globalAlpha *= (o.alpha ?? 1); ctx.fillStyle = o.caretColor || o.color || COL.ink;
    ctx.fillRect(x + w + sz * 0.06, y - sz * 0.8, Math.max(2, sz * 0.06), sz * 0.95); ctx.restore();
  }
  return n;
}
const typeTimes = (s, t0, cps = 18) => [...s].map((c, i) => [t0 + i / cps, c]).filter(([, c]) => c.trim());

// ---------------------------------------------------------------- 文字块：给一个矩形和一段话，自动断行、定字号、对齐、入场
// 可读下限：屏幕字高（大写 H 的高度，像素）。和 tools/layout.py 的「字太小」同一口径：宣传片短边 × 0.022，讲解片短边 × 0.015。
// 引擎只用它定 textBlock 的默认最小字号（o.min 可以改），不拦任何绘制；字太小由体检报告。
const MIN_TEXT_PX = Math.min(W, H) * (GENRE === 'explainer' ? 0.015 : 0.022);
// 每种角色的默认字体族、字重、最大字号（× U）、颜色。默认值只是起点，都写在这里；单次调用用 o.family、o.weight、o.max、o.color 覆盖。
const TEXT_ROLES = {
  title:   { family: 'display', weight: 700, max: 132, color: 'ink', balance: true },
  body:    { family: 'body', weight: 500, max: 54, color: 'ink', balance: false },
  label:   { family: 'body', weight: 600, max: 40, color: 'ink2', balance: true },
  number:  { family: 'display', weight: 700, max: 220, color: 'ink', balance: true },
  caption: { family: 'body', weight: 400, max: 34, color: 'ink2', balance: false },
};
// 少一行只损失这么多字号以内时，取行数少的那个（短标题不被拆成「动力来 / 自叶子」）；1 = 严格取最大字号
const TEXT_FEWER_LINES = 0.8;
// textBlock(ctx, text, box, o) → {x, y, w, h, size, lines: [{text, x, y, w}], fits}
//   在 box（当前变换下的版面坐标）里排一段字：中文按字断并遵守避头尾，英文按词断（单词不拆开），\n 强制换行。
//   字号自动取 [o.min, o.max] 里能放进 box、行数不超过 o.lines 的最大值；o.size 指定时不自动。
//   o.min 默认是可读下限 MIN_TEXT_PX 换算成这个字体的字号（可以改小，体检会报字太小）；o.max 默认按 role。返回值里 x, y, w, h 是字的外框，lines[i].y 是第 i 行的基线。
//   o.role 'title' | 'body'（默认）| 'label' | 'number' | 'caption'：决定字体族（theme.fonts）、字重、o.max、默认颜色。
//   排版：o.align 'left'（默认）| 'center' | 'right'；o.valign 'top'（默认）| 'middle' | 'bottom'；o.lh 行高（默认 1.25）；o.ls 字距 px；
//        一段折成几行时：title、label、number 各行等长，body、caption 只避免末行只剩一个字（TEXT_ROLES 的 balance）；
//        o.sizeText 按这段字定字号（会变的数字写最宽的那个值，字号就不跳；几块并列的字写最长的那句，字号就一致）。
//   颜色：o.color；o.colors 按原文逐字给颜色（colorRange(text, [[起, 止, 颜色]])，\n 也算一个字）；o.alpha。
//   入场：o.t 当前时间、o.at 入场时刻（两个都给才有入场）；o.style 'rise'（默认，riseLine 逐字升起，逐行错开 0.1 秒）
//        | 'slam'（slamLine 砸字，重拍用）| 'fade' | 'type'（打字机，o.cps 字/秒）| 'none'；o.out 0–1 退场进度（淡出并上移 0.12 个字号，
//        字不离开自己的区域，体检不会误报出框；要整行推出画面的换词用 rollWords）。
//        讲解片的 rise 不回弹（阻尼 0.85），宣传片沿用 riseLine 的弹性；o.z、o.f、o.charGap（逐字错开的秒数）照传给 riseLine / slamLine。
//   字号：取能放下的最大字号；少一行只小 20% 以内时取行数少的（TEXT_FEWER_LINES），给了 o.lines 就严格按最大字号。
//   o.anchor 名字：给整块文字登记锚点（callout 可以从它出发）。
//   同框换句：同一镜头里，后入场的一段字落在另一段字的框里（位置和尺寸都相差不到画面短边的 2%）、文字不同，而前一段在它入场时还看得见
//        （可见度 > 0.15，比如标题还在退场），后一段自动推迟到前一段完全退出（o.out 到 1 或不再画）再入场，最多推迟 TEXT_CLASH_MAX 秒；
//        往 window.__TEXTCLASH 推 {shot, t: 原定入场时刻, a: 前一段, b: 后一段, delay: 推迟的秒数}，体检会提示。要两段同时出现就给不同的框。
//        每次调用往 window.__TEXTS 推 {box（画布像素）, text, alpha（这一刻的可见度 0–1）, shot, at}，main.js 每帧清空。
//   放不下（最小字号也放不下，或单个英文单词比 box 宽）时照最小字号照常画，不抛错：fits: false，往 window.__TEXTFIT 推 {text, box, size, shot}，
//   体检把它列进可选提示；字真的出框、压字时由体检的硬伤检查报。
//   字都经 txt / riseLine 画，体检量得到。排版结果按参数缓存，一帧里调用几十次也不慢。
// textBlockMeasure(text, box, o)：同样的排版，只量不画（先量标题占多高，再把剩下的区域分给图）。
// 例：textBlock(ctx, '叶子散掉一点水，水就被往上拉一点', side, { role: 'title', valign: 'middle', t, at: ph('S04', 0) });
const _TB_NS = new Set([...'，。！？、；：）」』】》〉〕｝］’”…—～·・ー々ゝゞヽヾ%‰°′″,.!?;:)]}>»']);   // 不放行首
const _TB_NE = new Set([...'「『（【《〈〔｛［‘“([{<«$¥￥£€#']);                                 // 不放行尾
const _TB_CJK = /[\u2E80-\u2FFF\u3000-\u303F\u3040-\u30FF\u3100-\u31FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF\uF900-\uFAFF\uFE30-\uFE4F\uFF00-\uFFEF]/;
const _TBT = new Map(), _TBW = new Map(), _TBM = new Map(), _TBL = new Map(), _TBF = new Set();
function _tbReset() { _TBW.clear(); _TBM.clear(); _TBL.clear(); }      // 字体加载完后由 main.js 调用一次
const _tbFont = (fam, w, it, s) => `${it ? 'italic ' : ''}${w} ${s}px ${_ff(FONT[fam] || fam)}`;
function _tbMetrics(fam, w, it) {                                         // 100px 下的大写字高、字身上下沿（与字号成正比）
  const k = fam + '|' + w + '|' + it; let m = _TBM.get(k); if (m) return m;
  _M.font = _tbFont(fam, w, it, 100); _M.letterSpacing = '0px';
  const h = _M.measureText('H'), s = _M.measureText('国第黄霸Hgjpqy（）「」');   // 上下沿取高的汉字和括号，保证字形不出 box
  m = { cap: (h.actualBoundingBoxAscent + h.actualBoundingBoxDescent) / 100, asc: s.actualBoundingBoxAscent / 100, desc: s.actualBoundingBoxDescent / 100 };
  _TBM.set(k, m); return m;
}
function _tbTokens(text) {                                                // 段落 → 不可拆的单元（避头尾的标点粘到相邻的字上）
  let P = _TBT.get(text); if (P) return P;
  const ch = Array.from(text), last = s => { const a = Array.from(s); return a[a.length - 1]; }; P = [];
  let para = [], i = 0;
  const push = tk => {
    const u = para[para.length - 1];
    if (!tk.sp && u && !u.sp && (_TB_NS.has(Array.from(tk.s)[0]) || _TB_NE.has(last(u.s)))) { u.s += tk.s; u.n += tk.n; return; }
    para.push(tk);
  };
  while (i < ch.length) {
    const c = ch[i];
    if (c === '\n') { P.push(para); para = []; i++; continue; }
    if (/\s/.test(c)) { let j = i; while (j < ch.length && ch[j] !== '\n' && /\s/.test(ch[j])) j++; push({ s: ch.slice(i, j).join(''), i, n: j - i, sp: true }); i = j; continue; }
    if (_TB_CJK.test(c) || _TB_NS.has(c) || _TB_NE.has(c)) { push({ s: c, i, n: 1 }); i++; continue; }
    let j = i + 1; while (j < ch.length && !/\s/.test(ch[j]) && !_TB_CJK.test(ch[j]) && !_TB_NE.has(ch[j])) j++;
    push({ s: ch.slice(i, j).join(''), i, n: j - i }); i = j;
  }
  P.push(para); _TBT.set(text, P); return P;
}
function _tbWidths(P, font) {                                             // 每个单元在 100px 下的宽度
  const k = font + '\u0001' + P.map(p => p.map(u => u.s).join('\u0002')).join('\n'); let ws = _TBW.get(k); if (ws) return ws;
  _M.font = font; _M.letterSpacing = '0px'; ws = P.map(p => p.map(u => _M.measureText(u.s).width));
  if (_TBW.size > 4000) _TBW.clear(); _TBW.set(k, ws); return ws;
}
function _tbPara(para, wp, k, ls, maxW) {                                 // 一段贪心断行；k = 字号 / 100
  const lines = []; let over = false, cur = [], w = 0, sp = null;
  para.forEach((u, ui) => {
    const uw = wp[ui] * k + ls * u.n;
    if (u.sp) { if (cur.length) sp = [u, uw]; return; }
    if (uw > maxW + 0.01) over = true;
    const add = (sp ? sp[1] : 0) + uw;
    if (cur.length && w + add > maxW + 0.01) { lines.push({ u: cur, w }); cur = [u]; w = uw; }
    else { if (sp) cur.push(sp[0]); cur.push(u); w += add; }
    sp = null;
  });
  lines.push({ u: cur, w });
  return { lines, over };
}
function _tbWrap(P, ws, k, ls, maxW) {
  const lines = []; let over = false;
  P.forEach((para, pi) => { const r = _tbPara(para, ws[pi], k, ls, maxW); lines.push(...r.lines); over = over || r.over; });
  return { lines, over, maxw: Math.max(0, ...lines.map(l => l.w)) };
}
// 一段折成几行时收窄行宽、行数不变，各行等长；balance 关时只处理末行只剩一个字（一个词）的段落
function _tbBalance(P, ws, k, ls, maxW, all) {
  const lines = [];
  P.forEach((para, pi) => {
    let r = _tbPara(para, ws[pi], k, ls, maxW); const n = r.lines.length, last = r.lines[n - 1].u.filter(u => !u.sp).length;
    if (n > 1 && !r.over && (all || last <= 1)) {
      let lo = maxW * 0.4, hi = maxW;
      for (let j = 0; j < 10; j++) { const m = (lo + hi) / 2, t2 = _tbPara(para, ws[pi], k, ls, m); if (t2.lines.length === n && !t2.over) hi = m; else lo = m; }
      const rb = _tbPara(para, ws[pi], k, ls, hi); if (rb.lines.length === n) r = rb;
    }
    lines.push(...r.lines);
  });
  return { lines, over: false, maxw: Math.max(0, ...lines.map(l => l.w)) };
}
function _tbOpts(o) {
  const R = TEXT_ROLES[o.role || 'body']; if (!R) throw new Error(`textBlock 不认识的 role：${o.role}（可用 ${Object.keys(TEXT_ROLES).join('、')}）`);
  const family = o.family || R.family, weight = o.weight || R.weight, italic = !!o.italic, M = _tbMetrics(family, weight, italic);
  const min = o.min ?? MIN_TEXT_PX / (M.cap || 0.7) * 1.02, max = Math.max(min, o.max ?? R.max * U);
  return { R, family, weight, italic, M, min, max, lh: o.lh ?? 1.25, ls: o.ls || 0, lines: o.lines || Infinity, balance: R.balance };
}
function _tbLayout(text, box, o) {
  text = String(text ?? ''); const B = _bx(box), Q = _tbOpts(o);
  const key = [text, B.x, B.y, B.w, B.h, o.role, Q.family, Q.weight, Q.italic, Q.min, Q.max, o.size, Q.lines, Q.lh, Q.ls, o.align, o.valign, Q.balance, o.sizeText].join('\u0001');
  const hit = _TBL.get(key); if (hit) return hit;
  const f100 = _tbFont(Q.family, Q.weight, Q.italic, 100), P = _tbTokens(text), ws = _tbWidths(P, f100);
  const hOf = (s, n) => s * (Q.M.asc + Q.M.desc) + (n - 1) * s * Q.lh;
  const ok = (r, s) => !r.over && r.lines.length <= Q.lines && r.maxw <= B.w + 0.01 && hOf(s, r.lines.length) <= B.h + 0.01;
  const at = s => _tbWrap(P, ws, s / 100, Q.ls, B.w);
  const best = nl => {                                                     // 行数不超过 nl 时能放下的最大字号；放不下返回 0
    const ok2 = s => { const r = at(s); return ok(r, s) && r.lines.length <= nl; };
    if (ok2(Q.max)) return Q.max; if (!ok2(Q.min)) return 0;
    let lo = Q.min, hi = Q.max; for (let k = 0; k < 14 && hi - lo > 0.25; k++) { const m = (lo + hi) / 2; if (ok2(m)) lo = m; else hi = m; } return lo;
  };
  let size, fits;
  if (o.size) { size = o.size; fits = ok(at(size), size); }
  else if (o.sizeText !== undefined && String(o.sizeText) !== text) { const L0 = _tbLayout(o.sizeText, B, Object.assign({}, o, { sizeText: undefined })); size = L0.size; fits = ok(at(size), size); }
  else {
    size = best(Q.lines); fits = size > 0; if (!fits) size = Q.min;
    if (fits && !o.lines && TEXT_FEWER_LINES < 1) {
      const n = at(size).lines.length;
      for (let nl = P.length; nl < n; nl++) { const s2 = best(nl); if (s2 >= size * TEXT_FEWER_LINES) { size = s2; break; } }
    }
  }
  // 用真实字宽复核（逐单元相加和整行量出来的宽度有亚像素差）；超出就按比例缩一点
  const font = _tbFont(Q.family, Q.weight, Q.italic, size);
  let r = at(size), real = r.lines.map(l => measure(l.u.map(u => u.s).join(''), font, Q.ls));
  for (let k = 0; k < 3 && !o.size && fits && Math.max(0, ...real) > B.w + 0.5; k++) {
    size = Math.max(Q.min, size * B.w / Math.max(...real) * 0.998); r = at(size);
    const f2 = _tbFont(Q.family, Q.weight, Q.italic, size); real = r.lines.map(l => measure(l.u.map(u => u.s).join(''), f2, Q.ls));
  }
  if (!r.over && r.lines.length > P.length) r = _tbBalance(P, ws, size / 100, Q.ls, B.w, Q.balance);
  const F2 = _tbFont(Q.family, Q.weight, Q.italic, size), n = r.lines.length, bh = hOf(size, n);
  const top = o.valign === 'middle' ? B.y + (B.h - bh) / 2 : o.valign === 'bottom' ? B.y + B.h - bh : B.y;
  const lines = r.lines.map((l, i) => {
    const s = l.u.map(u => u.s).join(''), w = measure(s, F2, Q.ls), idx = [];
    for (const u of l.u) for (let j = 0; j < u.n; j++) idx.push(u.i + j);
    const x = o.align === 'center' ? B.x + (B.w - w) / 2 : o.align === 'right' ? B.x + B.w - w : B.x;
    return Object.freeze({ text: s, x, y: top + Q.M.asc * size + i * size * Q.lh, w, idx });
  });
  const x0 = lines.length ? Math.min(...lines.map(l => l.x)) : B.x, x1 = lines.length ? Math.max(...lines.map(l => l.x + l.w)) : B.x;
  const out = Object.freeze({ x: x0, y: top, w: x1 - x0, h: bh, size, lines: Object.freeze(lines), fits: fits && !r.over, font: F2, box: B });
  if (_TBL.size > 3000) _TBL.clear(); _TBL.set(key, out); return out;
}
function textBlockMeasure(text, box, o = {}) { return _tbLayout(text, box, o); }
function _tbRuns(ctx, chars, cols, x, y, base) {                          // 一行字按颜色分段，经 txt 画
  if (!cols || !cols.some(Boolean)) return txt(ctx, chars.join(''), x, y, base);
  for (let k = 0; k < chars.length;) {
    const c = cols[k] || base.color; let j = k + 1; while (j < chars.length && (cols[j] || base.color) === c) j++;
    txt(ctx, chars.slice(k, j).join(''), x + (k ? measure(chars.slice(0, k).join(''), base.font, base.ls || 0) : 0), y, Object.assign({}, base, { color: c })); k = j;
  }
}
function textBlock(ctx, text, box, o = {}) {
  const L = _tbLayout(text, box, o), Q = _tbOpts(o), shot = SHOT_NOW ?? null;
  if (!L.fits) {
    const k = shot + '\u0001' + L.font + '\u0001' + String(text) + '\u0001' + [L.box.x, L.box.y, L.box.w, L.box.h].map(v => Math.round(v)).join(',');
    if (!_TBF.has(k)) {
      _TBF.add(k); const b = L.box;
      window.__TEXTFIT.push({ text: String(text), box: { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.w), h: Math.round(b.h) }, size: Math.round(L.size * 10) / 10, shot });
      console.warn(`textBlock：「${String(text).slice(0, 24)}」在 ${shot || ''} 的 ${Math.round(b.w)}×${Math.round(b.h)} 区域里放不下，已照最小字号 ${L.size.toFixed(1)}px 画，可能超出这块区域`);
    }
  }
  const color = o.color || COL[Q.R.color] || COL.ink, alpha = o.alpha ?? 1, out = clamp(o.out || 0), anim = typeof o.t === 'number' && typeof o.at === 'number';
  const style = anim ? (o.style || 'rise') : 'none', t = o.t, gap = style === 'type' ? 0 : 0.1, size = L.size, str = String(text ?? ''), bp = _tbBoxPx(ctx, L.box);
  let at = o.at;
  if (anim && !_TB_PROBING && t >= at) {                                   // 同框换句：前一段还没退完就推迟入场
    const d = _tbDelay(shot, str, bp, at);
    if (d) { _tbClash(shot, at, d.a, str, d.until - at, bp); at = d.until; }
  }
  const vis = out >= 1 ? 0 : clamp(alpha * (1 - E.in2(out)) * (style === 'none' ? 1 : anim ? clamp((t - at) / 0.25) : 1));
  if (!_TB_PROBING && vis > 0.15)                                          // 同一帧里两段字压在同一个框里（推迟不了的情况）：只登记
    for (const e of window.__TEXTS) if (e.shot === shot && e.text !== str && e.alpha > 0.15 && _tbNear(e.box, bp)) _tbClash(shot, T_NOW, e.text, str, 0, bp);
  window.__TEXTS.push({ box: bp, text: str, alpha: Math.round(vis * 1000) / 1000, shot, at: anim ? o.at : null });
  if (o.anchor) anchor(ctx, o.anchor, L.x, L.y, L.w, L.h);
  if (out >= 1) return L;
  if (style === 'none' && at !== o.at && t < at) return L;
  const fa = alpha * (1 - E.in2(out)), dy = -E.inOut2(out) * size * 0.12;          // 退场：淡出并略微上移
  const base = { font: L.font, color, alpha: fa, ls: Q.ls };
  let tc = at;                                                             // 打字机：上一行打完，下一行才开始
  L.lines.forEach((ln, i) => {
    const chars = Array.from(ln.text), cols = o.colors ? ln.idx.map(j => o.colors[j] || null) : null;
    if (style === 'rise') {
      riseLine(ctx, ln.text, ln.x, ln.y + dy, t - at - i * gap, { font: L.font, size, ls: Q.ls, color, colors: cols, alpha: fa, z: o.z ?? (GENRE === 'explainer' ? 0.85 : 0.62), f: o.f, stagger: o.charGap });
    } else if (style === 'slam') {
      slamLine(ctx, ln.text, ln.x, ln.y + dy, t - at - i * gap, { font: L.font, size, ls: Q.ls, color, colors: cols, alpha: fa, f: o.f, z: o.z, stagger: o.charGap });
    } else if (style === 'fade') {
      const u = E.out3(prog(t, at + i * gap, o.dur ?? 0.5)); if (u > 0) _tbRuns(ctx, chars, cols, ln.x, ln.y + dy, Object.assign({}, base, { alpha: fa * u }));
    } else if (style === 'type') {
      const cps = o.cps || 18, t0 = tc + i * gap, nn = clamp(Math.floor((t - t0) * cps), 0, chars.length); tc = t0 + chars.length / cps;
      if (nn > 0) _tbRuns(ctx, chars.slice(0, nn), cols && cols.slice(0, nn), ln.x, ln.y + dy, base);
      const last = i === L.lines.length - 1, active = t >= t0 - 0.3 && (nn < chars.length || last) && (i === 0 || t >= t0);
      if (o.caret !== false && active && (nn < chars.length || Math.floor(t * 2.2) % 2 === 0)) {   // 光标和 typeOn 相同
        const w = measure(chars.slice(0, nn).join(''), L.font, Q.ls);
        ctx.save(); ctx.globalAlpha *= fa; ctx.fillStyle = o.caretColor || color;
        ctx.fillRect(ln.x + w + size * 0.06, ln.y + dy - size * 0.8, Math.max(2, size * 0.06), size * 0.95); ctx.restore();
      }
    } else _tbRuns(ctx, chars, cols, ln.x, ln.y + dy, base);
  });
  return L;
}
// ---------------------------------------------------------------- 同框换句（textBlock 内部用）
// 后一段要不要推迟、推迟到哪一刻，由「这个镜头在它原定入场那一刻画出来是什么样」决定：main.js 提供 window.__probeShot(镜头id, τ)，
// 在一块小的草稿画布上把这个镜头单独画一遍（不影响这一帧的画面和各项登记），返回那一刻的 __TEXTS。前一段在 τ = 入场时刻还看得见，
// 就二分找出它完全退出的时刻。结果只由镜头代码和这段字的参数决定，按参数缓存，每段字整片只算一次，跳到任意一帧结果都相同。
const TEXT_CLASH_MAX = 2;                 // 秒：前一段在这么久里都没退完，就不推迟（多半是两段字本来就同时显示），照常画并登记，体检会报
const _TBD = new Map(), _TBC = new Set();
let _TB_PROBING = false;
function _tbProbe(fn) { const p = _TB_PROBING; _TB_PROBING = true; try { return fn(); } finally { _TB_PROBING = p; } }   // main.js 的 __probeShot 用
window.__TEXTS = []; window.__TEXTCLASH = [];
function _tbBoxPx(ctx, B) {                                                // 当前变换下的框 → 画布像素的外接矩形
  const m = ctx.getTransform(), P = [[B.x, B.y], [B.x + B.w, B.y], [B.x, B.y + B.h], [B.x + B.w, B.y + B.h]].map(([x, y]) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f]);
  const xs = P.map(p => p[0]), ys = P.map(p => p[1]), x0 = Math.min(...xs), y0 = Math.min(...ys), r = v => Math.round(v * 10) / 10;
  return { x: r(x0), y: r(y0), w: r(Math.max(...xs) - x0), h: r(Math.max(...ys) - y0) };
}
function _tbNear(a, b) { const e = Math.min(W, H) * 0.02; return Math.abs(a.x - b.x) < e && Math.abs(a.y - b.y) < e && Math.abs(a.w - b.w) < e && Math.abs(a.h - b.h) < e; }
function _tbClash(shot, t, a, b, delay, box) {
  const k = shot + '\u0001' + a + '\u0001' + b; if (_TBC.has(k)) return; _TBC.add(k);
  window.__TEXTCLASH.push({ shot, t: Math.round(t * 1000) / 1000, a, b, delay: Math.round(delay * 1000) / 1000, box });
  if (!delay) console.warn(`textBlock：${shot || ''} 在 ${t.toFixed(2)} 秒，「${String(b).slice(0, 16)}」和「${String(a).slice(0, 16)}」同时出现在同一个框里，字会叠在一起；让前一段先退场（o.out），或给它们不同的框`);
}
function _tbDelay(shot, text, bp, at) {
  const key = [shot, text, bp.x, bp.y, bp.w, bp.h, at.toFixed(4)].join('\u0001');
  if (_TBD.has(key)) return _TBD.get(key);
  let res = null; const P = window.__probeShot;
  if (P && shot) {
    const other = tau => {                                                 // τ 时刻同框、不同文字、先入场的那段字的最大可见度
      const L = P(shot, tau) || [], self = L.findIndex(e => e.text === text && e.at !== null && Math.abs(e.at - at) < 1e-6 && _tbNear(e.box, bp));
      let v = 0, who = null;
      L.forEach((e, i) => {
        if (e.text === text || !_tbNear(e.box, bp)) return;
        if (e.at !== null && Math.abs(e.at - at) < 1e-6 && (self < 0 || i > self)) return;   // 同时入场的，后调用的让先调用的
        if (e.alpha > v) { v = e.alpha; who = e.text; }
      });
      return [v, who];
    };
    const [v0, who] = other(at + 1e-3);
    if (v0 > 0.15) {
      let lo = at, hi = at + TEXT_CLASH_MAX;
      if (other(hi)[0] > 0.01) res = { until: at, a: who };                // 一直不退：不推迟，只登记
      else { for (let k = 0; k < 10; k++) { const m = (lo + hi) / 2; if (other(m)[0] > 0.01) lo = m; else hi = m; } res = { until: hi, a: who }; }
    }
  }
  if (_TBD.size > 4000) _TBD.clear(); _TBD.set(key, res); return res;
}
window.__TEXTFIT = [];

// ---------------------------------------------------------------- 字幕层：按配音短句在底部字幕带烧录字幕
// project.json：
//   "subtitles": {"burn": true, "langs": ["zh", "en"], "size": "auto", "style": "shadow"}
//   burn 打开烧录；langs 一行一种语言，从上到下，最多两种；size "auto"（1080p 下第一种语言 48px，按短边换算）或数字（同口径）；
//   style "shadow"（默认：ink 色的字带一圈底色光晕，压到画面上也读得清）| "bar"（ink 色的半透明底条上写底色的字，画面复杂、字幕常压在图上时用）；
//   band 字幕带占安全区高度的比例（默认 0.12，两种语言 0.18）。字幕带的位置和 safeBox() 的让位见「持续运动」一节的 SUBS。
// 数据：timeline.json 每个镜头的 phrases（配音稿按标点切出的短句，带对齐好的 t0、t1）。配音的语言取 phrase.text（有汉字算 zh，否则算 en），
//   其他语言取 phrase[语言代码]，例如 phrase.en：来自 script/vo.json 每个镜头的 "en": [每个短句一条译文]，由 tools/timeline.py 写进时间轴。
// 时刻：短句开始时出现，结束后再留 SUB_TAIL 秒（不超过下一句的开始）；更长的空隙（镜头之间）不显示。
// 排版：居中，贴字幕带底边；每种语言自动断行，最多两行，放不下时整体缩小（最小到 75%）；第二种语言的字号是第一种的 72%。
// 画法：main.js 的 render 在所有镜头和模块的 overlay 之后、后期层之前调用 _subsDraw，屏幕坐标，不受镜头矩阵、转场位移、震动影响，
//   也不参与运动模糊。字经 txt() 画（不是装饰字，体检照常量字号）；画的时候 ctx.__role = 'subtitle'，版面检查据此把字幕和画面里的字分开。
// 登记：window.__SUBS = {on, langs, style, box: 字幕带 {x, y, w, h}, cue: 这一帧显示的 {t0, t1, lines: {zh: '…', en: '…'}} 或 null}，每帧更新；
//   每种语言的一块字往 window.__TEXTS 推 {box, text, alpha: 1, shot: null, at: 短句开始, role: 'subtitle', lang}。
const SUB_TAIL = 0.25, SUB_LH = 1.2, SUB_SCALES = [1, 0.92, 0.84, 0.75];
const _subBox = B => B && { x: Math.round(B.x), y: Math.round(B.y), w: Math.round(B.w), h: Math.round(B.h) };
window.__SUBS = { on: SUBS.on, langs: SUBS.langs.slice(), style: SUBS.style, box: _subBox(SUBS.band), cue: null };
let _SUBQ = null;
const _SUBL = new Map(), _SUBW = new Set();
function _subCues() {                                                      // 全片短句按时间排好，每句的显示区间 [a, z)
  if (_SUBQ) return _SUBQ;
  const P = Object.values(TL.scenes).flatMap(s => s.phrases || []).filter(p => isFinite(p.t0) && isFinite(p.t1) && String(p.text ?? '').trim()).sort((x, y) => x.t0 - y.t0);
  return (_SUBQ = P.map((p, i) => ({ p, a: p.t0, z: Math.min(p.t1 + SUB_TAIL, P[i + 1] ? P[i + 1].t0 : Infinity) })));
}
function _subAt(t) {
  const Q = _subCues(); let lo = 0, hi = Q.length - 1, k = -1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (Q[m].a <= t) { k = m; lo = m + 1; } else hi = m - 1; }
  return k >= 0 && t < Q[k].z ? Q[k] : null;
}
function _subText(p, lang) {                                               // 这个短句在 lang 下的字幕；句尾的逗号、顿号、分号、冒号去掉
  const clean = s => String(s ?? '').trim().replace(/[，、；：,;:]+$/, '');
  if (p[lang] !== undefined && lang !== 'text') return clean(p[lang]);
  if (lang === (_TB_CJK.test(String(p.text)) ? 'zh' : 'en')) return clean(p.text);
  const k = lang + '\u0001' + p.text;
  if (!_SUBW.has(k)) { _SUBW.add(k); console.warn(`字幕：短句「${String(p.text).slice(0, 20)}」没有 ${lang} 译文（phrase.${lang}），这一行不画。在 script/vo.json 这个镜头的 "${lang}" 里补上，再运行 tools/timeline.py`); }
  return '';
}
function _subLayout(lines) {                                               // lines = [[语言, 文字]] → {blocks: [{lang, text, L}], h, gap, w}
  const key = lines.map(l => l.join('\u0002')).join('\u0001'), hit = _SUBL.get(key); if (hit) return hit;
  const B = SUBS.band, w = B.w * 0.86, base = (SUBS.size === 'auto' ? 48 : SUBS.size) * U;
  let res = null;
  for (const s of SUB_SCALES) {
    const blocks = lines.map(([lang, text], i) => ({ lang, text, L: _tbLayout(text, _R(0, 0, w, 1e5), { role: 'label', family: 'body', weight: 500, size: base * s * (i ? 0.72 : 1), lh: SUB_LH, align: 'center' }) }));
    const gap = blocks.length > 1 ? 0.3 * blocks[1].L.size : 0, h = blocks.reduce((a, b) => a + b.L.h, 0) + gap;
    res = { blocks, h, gap, w, ok: blocks.every(b => b.L.fits && b.L.lines.length <= 2) && h <= B.h };
    if (res.ok) break;
  }
  if (!res.ok) console.warn(`字幕：「${lines.map(l => l[1]).join(' / ').slice(0, 40)}」缩到 75% 仍超过两行或超出字幕带，拆短这一句的配音（多加一个逗号），或调大 subtitles.band`);
  if (_SUBL.size > 2000) _SUBL.clear(); _SUBL.set(key, res); return res;
}
function _subsDraw(ctx, t) {
  const S = window.__SUBS = { on: SUBS.on, langs: SUBS.langs.slice(), style: SUBS.style, box: _subBox(SUBS.band), cue: null };
  if (!SUBS.on) return;
  const q = _subAt(t); if (!q) return;
  const lines = SUBS.langs.map(l => [l, _subText(q.p, l)]).filter(l => l[1]);
  S.cue = { t0: q.a, t1: Math.round(q.z * 1e4) / 1e4, lines: Object.fromEntries(lines) };
  if (!lines.length) return;
  const B = SUBS.band, R = _subLayout(lines), bar = SUBS.style === 'bar', base = R.blocks[0].L.size, padX = 0.5 * base, padY = 0.22 * base;
  const ox = B.x + (B.w - R.w) / 2, top0 = B.y + B.h - (bar ? padY : 0) - R.h;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.filter = 'none';
  const role0 = ctx.__role; ctx.__role = 'subtitle';
  try {
    if (bar) {
      const x0 = ox + Math.min(...R.blocks.map(b => b.L.x)), x1 = ox + Math.max(...R.blocks.map(b => b.L.x + b.L.w));
      ctx.fillStyle = hexA(COL.ink, 0.72); rrect(ctx, x0 - padX, top0 - padY, x1 - x0 + 2 * padX, R.h + 2 * padY, 0.25 * base); ctx.fill();
    } else { ctx.shadowColor = COL.bg; ctx.shadowBlur = 0.3 * base; }
    let y = top0;
    for (const b of R.blocks) {
      for (const ln of b.L.lines) txt(ctx, ln.text, ox + ln.x, y + ln.y, { font: b.L.font, color: bar ? COL.bg : COL.ink });
      window.__TEXTS.push({ box: _subBox({ x: ox + b.L.x, y, w: b.L.w, h: b.L.h }), text: b.text, alpha: 1, shot: null, at: q.a, role: 'subtitle', lang: b.lang });
      y += b.L.h + R.gap;
    }
  } finally { ctx.__role = role0; ctx.restore(); }
}
// ---------------------------------------------------------------- 形状与线
function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function pathLen(pts) { let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); return L; }
// 折线按进度 u 画出，可带箭头；返回笔尖位置
function drawPath(ctx, pts, u, o = {}) {
  if (u <= 0) return null;
  const L = pathLen(pts) * clamp(u);
  ctx.save(); ctx.strokeStyle = o.color || COL.ink; ctx.lineWidth = o.lw || 3; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.globalAlpha *= (o.alpha ?? 1);
  if (o.dash) ctx.setLineDash(o.dash);
  ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
  let acc = 0, end = pts[0], ang = 0;
  for (let i = 1; i < pts.length; i++) {
    const [ax, ay] = pts[i - 1], [bx, by] = pts[i], d = Math.hypot(bx - ax, by - ay); ang = Math.atan2(by - ay, bx - ax);
    if (acc + d >= L) { const k = (L - acc) / d; end = [ax + (bx - ax) * k, ay + (by - ay) * k]; ctx.lineTo(end[0], end[1]); break; }
    acc += d; ctx.lineTo(bx, by); end = [bx, by];
  }
  ctx.stroke();
  if (o.arrow && u > 0.02) {
    ctx.setLineDash([]); ctx.fillStyle = o.color || COL.ink; const a = o.arrow;
    ctx.beginPath(); ctx.moveTo(end[0] + Math.cos(ang) * a * 0.4, end[1] + Math.sin(ang) * a * 0.4);
    ctx.lineTo(end[0] - Math.cos(ang - 0.5) * a, end[1] - Math.sin(ang - 0.5) * a); ctx.lineTo(end[0] - Math.cos(ang + 0.5) * a, end[1] - Math.sin(ang + 0.5) * a); ctx.closePath(); ctx.fill();
  }
  ctx.restore(); return end;
}

// ---------------------------------------------------------------- 图片与图片序列
// web/img/ 下的文件在 project.json 的 assets.images 里列出（或由 tools/timeline.py 自动扫描），main.js 开始渲染前全部解码完。
// 名字去掉扩展名：img/logo.png → IMG.logo；img/clip/0001.jpg 序列 → SEQ.clip = [Image, ...]
const IMG = {}, SEQ = {};
async function loadAssets() {
  const A = PROJECT.assets || {};
  const one = async (path, key, bag) => { const im = new Image(); im.src = 'img/' + path; try { await im.decode(); } catch (e) { throw new Error('图片解码失败：img/' + path); } bag[key] = im; };
  await Promise.all((A.images || []).map(p => one(p, p.replace(/\.(png|jpe?g|webp|gif|svg)$/i, ''), IMG)));
  for (const [name, files] of Object.entries(A.sequences || {})) { SEQ[name] = []; await Promise.all(files.map((f, i) => one(name + '/' + f, i, SEQ[name]))); }
}
// 画图：fit = 'cover' | 'contain' | 'fill'；r 圆角；shadow 投影强度；src 可选源区域 [sx,sy,sw,sh]（截图局部放大用）
function img(ctx, im, x, y, w, h, o = {}) {
  if (typeof im === 'string') { const k = im; im = IMG[k]; if (!im) throw new Error('没有这张图：' + k); }
  let [sx, sy, sw, sh] = o.src || [0, 0, im.naturalWidth || im.width, im.naturalHeight || im.height];
  const fit = o.fit || 'cover';
  let dx = x, dy = y, dw = w, dh = h;
  if (fit === 'cover') { const s = Math.max(w / sw, h / sh), cw = w / s, ch = h / s; sx += (sw - cw) * (o.ax ?? 0.5); sy += (sh - ch) * (o.ay ?? 0.5); sw = cw; sh = ch; }
  else if (fit === 'contain') { const s = Math.min(w / sw, h / sh); dw = sw * s; dh = sh * s; dx = x + (w - dw) * (o.ax ?? 0.5); dy = y + (h - dh) * (o.ay ?? 0.5); }
  ctx.save(); ctx.globalAlpha *= (o.alpha ?? 1);
  if (o.shadow) { ctx.save(); ctx.shadowColor = `rgba(0,0,0,${0.55 * o.shadow})`; ctx.shadowBlur = 60 * U * o.shadow; ctx.shadowOffsetY = 24 * U * o.shadow; ctx.fillStyle = '#000'; rrect(ctx, dx, dy, dw, dh, o.r || 0); ctx.fill(); ctx.restore(); }
  if (o.r) { rrect(ctx, dx, dy, dw, dh, o.r); ctx.clip(); }
  ctx.drawImage(im, sx, sy, sw, sh, dx, dy, dw, dh);
  if (o.border) { ctx.strokeStyle = o.border; ctx.lineWidth = o.borderW || 1.5; rrect(ctx, dx, dy, dw, dh, o.r || 0); ctx.stroke(); }
  ctx.restore();
  return [dx, dy, dw, dh];
}
// 序列帧：按本地时间 lt 和帧率取一帧（素材视频先用 tools/assets.py frames 拆成序列）
function seqFrame(name, lt, fps = 30, loop = false) { const a = SEQ[name]; if (!a || !a.length) return null; let i = Math.floor(lt * fps); i = loop ? ((i % a.length) + a.length) % a.length : clamp(i, 0, a.length - 1); return a[i]; }

// ---------------------------------------------------------------- 应用窗口外框
// 把截图装进一个应用窗口（标题栏、红黄绿按钮、可选地址栏、圆角、细边框），返回离屏 canvas，可直接交给 img() 和 GL3D.card。
// 透明底的产品截图直接放在深色背景上会像飘着，加外框和实底就有了「这是一个窗口」的重量。
// src：IMG 里的名字或 Image / Canvas。o：{ url 有则画浏览器地址栏, title 无地址栏时居中的窗口标题, dark 深色窗口, w, h 内容区尺寸（默认 w=图宽，最大 1800，h 按图片比例）,
//   r 圆角, bg 内容区底色 }。画好的 canvas 按参数缓存，只画一次；src 是 Canvas 且内容会变时换新对象。canvas.static=true：GL3D.card 只上传一次纹理。
// 在镜头函数或 window.INIT 里调用都行（字体已加载）。窗口总高 = 标题栏 + h，标题栏高度按 w 缩放（1280 宽时 44px）。
const _AW = new Map(), _awId = new WeakMap(); let _awN = 0;
function appWindow(src, o = {}) {
  const im = typeof src === 'string' ? IMG[src] : src; if (!im) throw new Error('appWindow 没有这张图：' + src);
  const iw = im.naturalWidth || im.width, ih = im.naturalHeight || im.height;
  const w = Math.round(o.w || Math.min(iw, 1800)), h = Math.round(o.h || w * ih / iw);
  if (typeof src !== 'string' && !_awId.has(src)) _awId.set(src, ++_awN);
  const key = (typeof src === 'string' ? src : _awId.get(src)) + JSON.stringify([o.url, o.title, !!o.dark, w, h, o.r, o.bg]);
  if (_AW.has(key)) return _AW.get(key);
  const s = w / 1280, bar = Math.round((o.url ? 52 : 44) * s), r = o.r ?? Math.round(14 * s), dk = !!o.dark;
  const c = document.createElement('canvas'); c.width = w; c.height = bar + h; const g = c.getContext('2d');
  g.beginPath(); g.roundRect(0, 0, w, bar + h, r); g.clip();
  g.fillStyle = o.bg || (dk ? '#17181B' : '#FFFFFF'); g.fillRect(0, 0, w, bar + h);
  g.fillStyle = dk ? '#2B2C30' : '#ECECEE'; g.fillRect(0, 0, w, bar);
  g.fillStyle = dk ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.10)'; g.fillRect(0, bar - 1, w, 1);
  ['#FF5F57', '#FEBC2E', '#28C840'].forEach((col, i) => { g.fillStyle = col; g.beginPath(); g.arc((22 + i * 20) * s, bar / 2, 6.5 * s, 0, Math.PI * 2); g.fill(); });
  const tc = dk ? '#A3A8B0' : '#6B6B72';
  if (o.url) {
    const pw = Math.min(w * 0.52, 620 * s), ph = 28 * s, px = (w - pw) / 2;
    g.fillStyle = dk ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'; g.beginPath(); g.roundRect(px, (bar - ph) / 2, pw, ph, ph / 2); g.fill();
    txt(g, o.url, w / 2, bar / 2, { font: F.b(14 * s, 500), color: tc, align: 'center', base: 'middle' });
  } else if (o.title) txt(g, o.title, w / 2, bar / 2, { font: F.b(14 * s, 600), color: tc, align: 'center', base: 'middle' });
  img(g, im, 0, bar, w, h, { fit: 'cover' });
  g.strokeStyle = dk ? 'rgba(255,255,255,0.14)' : 'rgba(0,0,0,0.18)'; g.lineWidth = 1; g.beginPath(); g.roundRect(0.5, 0.5, w - 1, bar + h - 1, r); g.stroke();
  c.static = true; _AW.set(key, c); return c;
}

// ---------------------------------------------------------------- 碎片拼合
// 把一张图（logo、字标、截图，IMG 名字或 Image / Canvas）切成网格碎片，p = 0 时散在四周，p = 1 时严丝合缝拼回原图。
// 反过来炸开就传 1 - p。只切有内容的格子：透明部分（logo 的底）不产生碎片，所以拼出来是 logo 的形状而不是一个方块。
// (x, y, w, h) 是拼好后图在画面上的位置。o：{ cols 列数(默认 16), rows 行数(按比例), shape 'tri'|'sq', spread 散开距离(默认画面短边 0.6),
//   rot 最大旋转弧度(默认 1.2), stagger 碎片先后到达的时间差占比(默认 0.35，越大越像一片片飞来), from [fx, fy] 碎片飞来的中心(默认图中心，
//   传画面外的点就是从一侧涌入), seed, ease 缓动(默认 E.out3), alpha }。
// 用法：拼合放在落版前 1–2 拍，拼好就停，不要把整段都给拼合。p 用 land() 或 prog() 算，保证拍点那一帧碎片已经飞到一半以上。
const _SH = new Map();
function _shatterCells(im, cols, rows, iw, ih) {
  const key = im; let byGrid = _SH.get(key); if (!byGrid) { byGrid = new Map(); _SH.set(key, byGrid); }
  const gk = cols + 'x' + rows; if (byGrid.has(gk)) return byGrid.get(gk);
  const c = document.createElement('canvas'); c.width = cols * 4; c.height = rows * 4; const g = c.getContext('2d');
  g.drawImage(im, 0, 0, c.width, c.height); const d = g.getImageData(0, 0, c.width, c.height).data;
  const on = []; for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    let s = 0; for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) s += d[((j * 4 + y) * c.width + i * 4 + x) * 4 + 3];
    on.push(s / (16 * 255) > 0.04);
  }
  byGrid.set(gk, on); return on;
}
function shatter(ctx, src, x, y, w, h, p, o = {}) {
  const im = typeof src === 'string' ? IMG[src] : src; if (!im) throw new Error('shatter 没有这张图：' + src);
  if (p <= 0 && !o.showAtZero) return;
  const iw = im.naturalWidth || im.width, ih = im.naturalHeight || im.height;
  const cols = o.cols || 16, rows = o.rows || Math.max(1, Math.round(cols * h / w)), cw = w / cols, ch = h / rows;
  const on = _shatterCells(im, cols, rows, iw, ih), r = rng(o.seed || 7), ease = o.ease || E.out3;
  const spread = (o.spread ?? 0.6) * Math.min(W, H), rotMax = o.rot ?? 1.2, st = clamp(o.stagger ?? 0.35, 0, 0.9);
  const [fx, fy] = o.from || [x + w / 2, y + h / 2];
  ctx.save(); ctx.globalAlpha *= (o.alpha ?? 1);
  const tri = (o.shape || 'tri') === 'tri';
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    const r1 = r(), r2 = r(), r3 = r(), r4 = r(), r5 = r(), r6 = r();
    if (!on[j * cols + i]) continue;
    const parts = tri ? [0, 1] : [0];
    for (const k of parts) {
      const rr = k ? [r4, r5, r6] : [r1, r2, r3];
      const delay = rr[0] * st, e = ease(clamp((p - delay) / (1 - st)));
      if (e <= 0 && p < 1) continue;
      const px = x + (i + 0.5) * cw, py = y + (j + 0.5) * ch;
      let dx = px - fx, dy = py - fy; const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;
      const ang = Math.atan2(dy, dx) + (rr[1] - 0.5) * 1.2, dist = spread * (0.5 + rr[2]) * (1 - e);
      const ox = Math.cos(ang) * dist, oy = Math.sin(ang) * dist, rot = (rr[1] - 0.5) * 2 * rotMax * (1 - e);
      ctx.save(); ctx.globalAlpha *= clamp(e * 2.5);
      ctx.translate(px + ox, py + oy); ctx.rotate(rot); ctx.translate(-px, -py);
      ctx.beginPath();
      const x0 = x + i * cw, y0 = y + j * ch, pad = 0.6;
      if (!tri) ctx.rect(x0 - pad, y0 - pad, cw + pad * 2, ch + pad * 2);
      else if (k === 0) { ctx.moveTo(x0 - pad, y0 - pad); ctx.lineTo(x0 + cw + pad, y0 - pad); ctx.lineTo(x0 - pad, y0 + ch + pad); ctx.closePath(); }
      else { ctx.moveTo(x0 + cw + pad, y0 - pad); ctx.lineTo(x0 + cw + pad, y0 + ch + pad); ctx.lineTo(x0 - pad, y0 + ch + pad); ctx.closePath(); }
      ctx.clip();
      const sx = (i / cols) * iw, sy = (j / rows) * ih, sw = iw / cols, sh = ih / rows, mx = sw * 0.1, my = sh * 0.1;
      ctx.drawImage(im, Math.max(0, sx - mx), Math.max(0, sy - my), Math.min(iw - Math.max(0, sx - mx), sw + mx * 2), Math.min(ih - Math.max(0, sy - my), sh + my * 2),
        x0 - (sx - Math.max(0, sx - mx)) * w / iw, y0 - (sy - Math.max(0, sy - my)) * h / ih,
        Math.min(iw - Math.max(0, sx - mx), sw + mx * 2) * w / iw, Math.min(ih - Math.max(0, sy - my), sh + my * 2) * h / ih);
      ctx.restore();
    }
  }
  ctx.restore();
}

// ---------------------------------------------------------------- 光标
// macOS 风格箭头（默认白填黑边），(x, y) 是指尖。o：{ press 0..1 按下时缩小, scale, alpha, hand 手形（指向手，指尖在 (x, y)）, fill, line 反色光标换这两个颜色 }。
// UI 片用光标驱动点击和拖拽：光标位置用 springTo / camKeys 的关键点定，按钮的按下、拖动的值都从光标位置算出来，不要各写各的时间。
// 拖拽的写法：按下期间，被拖的值由光标位置直接算出（val = f(curX)），手和物体同一帧到位；松开（时刻 tr）以后，值从当时的位置弹向目标：
//   const v0 = f(curX(tr)); val = t < tr ? f(curX(t)) : lerp(v0, target, spring(t - tr, 3, 0.55));
// 点击：press 在按下时刻用 springTo 拉到 1、松开时拉回 0；被点的元素在同一时刻缩小，音效登记在按下的时刻。
function cursor(ctx, x, y, o = {}) {
  const a = (o.alpha ?? 1) * ctx.globalAlpha; if (a <= 0.003) return;
  const k = 1.3 * U * (o.scale ?? 1) * (1 - 0.14 * clamp(o.press ?? 0));      // 单位坐标里箭头高约 19.5，k 把它放到约 25px（1080p）
  ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.scale(k, k); ctx.lineJoin = 'round'; ctx.beginPath();
  if (o.hand) {
    ctx.translate(3.6, 0);
    [[-5.4, 0, 3.8, 12, 1.9], [-1.6, 5.4, 3.5, 8, 1.75], [1.9, 6.4, 3.5, 7, 1.75], [5.4, 7.6, 3.2, 6, 1.6], [-7.4, 10, 17, 9.5, 4], [-9.2, 11.4, 4, 6.5, 2]].forEach(p => ctx.roundRect(...p));
  } else {
    ctx.moveTo(0, 0); ctx.lineTo(0, 16.4); ctx.lineTo(3.9, 12.9); ctx.lineTo(6.5, 19); ctx.lineTo(9.1, 17.9); ctx.lineTo(6.6, 11.9); ctx.lineTo(11.7, 11.9); ctx.closePath();
  }
  ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = 5 * U; ctx.shadowOffsetY = 2 * U;
  ctx.strokeStyle = o.line || '#000'; ctx.lineWidth = 2.8; ctx.stroke();                 // 先描双倍宽的边再填充：内侧一半被填充盖住，只留外轮廓
  ctx.shadowColor = 'transparent'; ctx.fillStyle = o.fill || '#fff'; ctx.fill(); ctx.restore();
}

// ---------------------------------------------------------------- 后期层（不参与运动模糊）：颗粒、暗角、闪光、首尾淡入淡出
let _GRAIN = null;
function _grainInit() {
  _GRAIN = document.createElement('canvas'); _GRAIN.width = _GRAIN.height = 512;
  const g = _GRAIN.getContext('2d'), im = g.createImageData(512, 512), r = rng(PROJECT.seed || 1);
  for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() + r() + r() - 1.5) * 90; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
  g.putImageData(im, 0, 0);
}
function postFX(ctx, t, frame) {
  const P = Object.assign({ grain: 0.06, vignette: 0.3, fadeIn: 0, fadeOut: 0, fadeColor: '#000000' }, PROJECT.post || {});
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.filter = 'none';
  const [fa, fc, fm] = flashAt(t);
  if (fa > 0.003) { ctx.globalCompositeOperation = fm === 'add' ? 'lighter' : 'overlay'; ctx.globalAlpha = Math.min(1, fa); ctx.fillStyle = fc; ctx.fillRect(0, 0, W, H); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; }
  if (P.vignette > 0) { const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.45, W / 2, H / 2, Math.hypot(W, H) * 0.55); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${P.vignette})`); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
  if (P.grain > 0) {
    if (!_GRAIN) _grainInit();
    const r = rng(1000 + frame), ox = Math.floor(r() * 512), oy = Math.floor(r() * 512);
    ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = P.grain;
    for (let x = -ox; x < W; x += 512) for (let y = -oy; y < H; y += 512) ctx.drawImage(_GRAIN, x, y);
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
  }
  const fi = P.fadeIn > 0 ? 1 - clamp(t / P.fadeIn) : 0, fo = P.fadeOut > 0 ? clamp((t - (TL.total - P.fadeOut)) / P.fadeOut) : 0, f = Math.max(fi, fo);
  if (f > 0) { ctx.globalAlpha = E.in2(f); ctx.fillStyle = P.fadeColor; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
}
