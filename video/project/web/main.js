/* =========================================================
   main.js —— 启动（字体、图片、可选模块）与 window.render(t)
   镜头：SHOT.S01 = function (ctx, t, S) {...}            只在时间轴给它的 [S.t0, S.t1) 内画
         SHOT.S01 = { pre: 0.3, post: 0.5, draw(ctx, t, S) {...} }   向前/向后多画几秒，和相邻镜头重叠做转场
         SHOT.S01 = { a: 3.2, b: 6.0, draw(...) }         直接给绝对范围
   同一时刻有多个镜头时，开始得晚的画在上面（相同则按 id）。
   背景每帧由这里先画（theme.colors.bg；模块可用 STYLE.background 换掉）。镜头里不要铺底：铺底会把同一时刻
   画在下面的镜头整个盖掉，重叠转场就变成了硬切。只有转场设计上就要盖住上一个镜头时才在镜头里铺底。
   镜头间的通用转场（可选）：project.json 的 transitions，例如 { "default": "cut", "S03": { "type": "push", "dir": "left", "dur": 0.5 } }
   表示 S03 → 下一个镜头用横推。类型：cut（默认）、push（left/right/up/down）、fade。设计感强的转场请写在镜头里。
   帧率：project.json 的 fps。讲解片默认 30（画面以图形和文字为主，30 帧足够，渲染量减半），宣传片和动效片默认 60。
   锚点与标注：每帧绘制前清空 window.__ANCHORS 和 window.__LINKS（见 core.js「锚点与标注」）。开运动模糊时表里是快门中点那张子帧的记录，
   也就是 t 那一刻的。
   每帧登记（体检读）：window.__ACTS 画面事件（act），window.__CAMS 每个镜头的 cam 矩阵，window.__GLOBAL 全局后期变换（SHAKES 震动和底鼓缩放）
   [a, b, c, d, e, f]，window.__FRAME = {t, shots: 这一帧在画的镜头id, base: {镜头id: 这个镜头的 BASE（转场位移 × __GLOBAL）}}，
   window.__TEXTS 这一帧每次 textBlock 调用的 {box, text, alpha, shot, at}（字幕层的字也在里面，带 role: 'subtitle'），
   window.__SUBS 字幕层 {on, langs, style, box: 字幕带, cue: 这一帧的字幕或 null}。对任意 t 调 render(t) 之后读，就是这一帧的记录。
   绘制顺序：背景 → 镜头 → 模块的 STYLE.overlay → 字幕层（project.json 的 subtitles，见 core.js「字幕层」）→ 后期层。
   累计登记（不按帧清空）：window.__TEXTCLASH 同框换句被推迟或压在一起的字（见 core.js 的 textBlock），window.__MBSTAT 运动模糊的采样统计。
   window.__PROPS：启动后列出 PROP 里登记的全部物件 [{name, size}]。window.__probeShot(镜头id, τ)：在草稿画布上单独画一个镜头，返回那一刻的
   __TEXTS（textBlock 判断同框换句用），不改动这一帧的画面和登记。
   运动模糊（只在正式档，window.__MB_OFF 为真时每帧只画一次）：project.json 的 motion_blur = {samples 下限, shutter 快门占一帧的比例, max 上限}，
   每帧按画面变化自动定采样数，见 render() 前的说明。
   ========================================================= */
'use strict';
(async function () {
  if (window.__FATAL) throw new Error(window.__FATAL);       // core.js 启动时发现的配置错误（例如缺 theme.colors）
  const cv = document.getElementById('c');
  const ctx = cv.getContext('2d', { alpha: false });
  window.CTX = ctx;

  // 字体：等每个用到的字重加载完并预绘一次，否则前几帧会是系统默认字体
  const fams = [...new Set(Object.values(FONT))];
  const weights = (TH.weights || [400, 500, 600, 700, 800, 900]);
  const sample = (PROJECT.title || '') + ' ' + (TH.sample || '') + ' AaBbGgQq 0123456789 —·→%';
  const faces = [];
  for (const f of fams) for (const w of weights) faces.push(`${w} 100px ${_ff(f)}`);
  if (FONT.serif) faces.push(F.s(100, true), F.s(100, false));
  for (const f of faces) { try { await document.fonts.load(f, sample); } catch (e) { console.log('font load fail', f); } }
  await document.fonts.ready;
  for (const f of faces) { ctx.font = f; ctx.fillText(sample, -5000, -5000); }
  _tbReset();                                               // 文字块的字体度量要在字体加载完以后量

  await loadAssets();
  if (window.bgInit) await window.bgInit();
  for (const f of (window.INIT || [])) await f();          // 模块和镜头文件可以 push 异步初始化函数（离屏画布、预计算）
  window.__PROPS = Object.keys(PROP).map(name => {                       // 物件表（stills.py --props 读）；size 写错的记 null，prop() 画它时报错
    const z = PROP[name] && PROP[name].size; return { name, size: Array.isArray(z) && z.length === 2 && z[0] > 0 && z[1] > 0 ? z.slice() : null };
  });
  for (const p of window.__PROPS) if (!p.size) console.error(`PROP.${p.name}.size 缺失或写错：写 PROP.${p.name}.size = [宽, 高]（画这个物件时用的自然尺寸）`);

  const FPS = TL.fps || PROJECT.fps || 60;
  const ORDER = Object.values(TL.scenes).sort((x, y) => x.t0 - y.t0);
  const TR = PROJECT.transitions || {};
  const trOf = i => { const s = ORDER[i]; if (!ORDER[i + 1]) return null; const v = TR[s.id] ?? TR.default ?? 'cut'; const o = typeof v === 'string' ? { type: v } : v; return o.type === 'cut' ? null : Object.assign({ dur: 0.5, dir: 'left' }, o); };

  // 每个镜头的绘制范围
  const LIST = ORDER.map((S, i) => {
    const d = SHOT[S.id]; const fn = typeof d === 'function' ? d : d && d.draw;
    let a = d && d.a !== undefined ? d.a : S.t0 - ((d && d.pre) || 0), z = d && d.b !== undefined ? d.b : S.t1 + ((d && d.post) || 0);
    const tin = i > 0 ? trOf(i - 1) : null, tout = trOf(i);
    if (tin) a = Math.min(a, S.t0 - tin.dur / 2);
    if (tout) z = Math.max(z, S.t1 + tout.dur / 2);
    return { S, fn, a, z, i, tin, tout };
  });
  const extra = Object.keys(SHOT).filter(k => !TL.scenes[k]);
  if (extra.length) console.warn('这些镜头不在时间轴里，不会被画：' + extra.join(', '));
  const DRAW = LIST.slice().sort((x, y) => x.a - y.a || (x.S.id < y.S.id ? -1 : 1));

  // 通用转场：返回这个镜头此刻的位移和透明度
  function trState(L, t) {
    let ox = 0, oy = 0, al = 1;
    const apply = (tr, edge, entering) => {
      const u = E.inOut3(clamp((t - (edge - tr.dur / 2)) / tr.dur));
      if (tr.type === 'fade') { al *= entering ? u : (t < edge + tr.dur / 2 ? 1 : 0); return; }
      const dx = { left: -W, right: W, up: 0, down: 0 }[tr.dir] ?? -W, dy = { up: -H, down: H }[tr.dir] ?? 0;
      if (entering) { ox += -dx * (1 - u); oy += -dy * (1 - u); } else { ox += dx * u; oy += dy * u; }
    };
    if (L.tin && t < L.S.t0 + L.tin.dur / 2) apply(L.tin, L.S.t0, true);
    if (L.tout && t > L.S.t1 - L.tout.dur / 2) apply(L.tout, L.S.t1, false);
    return [ox, oy, al];
  }

  function stub(ctx, t, S) {
    screen(ctx); fillBg(ctx, COL.bg);
    txt(ctx, S.id + (S.label ? '  ' + S.label : ''), 80 * U, 160 * U, { font: F.m(48 * U, 600), color: COL.acc });
    txt(ctx, `${S.t0.toFixed(2)}–${S.t1.toFixed(2)}s`, 80 * U, 230 * U, { font: F.m(32 * U), color: COL.ink2 });
  }

  // 一帧（不含后期层）
  const MZ = (PROJECT.music || {}).kick_zoom || 0;
  function frame(c, t) {
    const [sx, sy, sr] = shake(t), k = MZ ? kickEnv(t) : 0, z = 1 + MZ * k;
    const G = new DOMMatrix().translate(W / 2 + sx, H / 2 + sy).rotate(sr * 180 / Math.PI).scale(z).translate(-W / 2, -H / 2);
    c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; c.filter = 'none';
    BASE = G; T_NOW = t; window.__ANCHORS = {}; window.__LINKS = []; window.__ACTS = []; window.__CAMS = {}; window.__TEXTS = [];
    const mx = M => [M.a, M.b, M.c, M.d, M.e, M.f];
    window.__GLOBAL = mx(G); window.__FRAME = { t, shots: [], base: {} };
    if (window.STYLE && STYLE.background) STYLE.background(c, t); else fillBg(c, COL.bg);
    if (window.BG && BG.ready && BG.on) {
      c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(BG.frame, 0, 0, W, H);
      const veil = PROJECT.background.veil || 0;                 // 在 shader 上盖一层底色，文字不够清楚时先加它
      if (veil > 0) { c.globalAlpha = veil; c.fillStyle = COL.bg; c.fillRect(0, 0, W, H); c.globalAlpha = 1; }
    }
    for (const L of DRAW) {
      if (t < L.a || t >= L.z) continue;
      const [ox, oy, al] = trState(L, t); if (al <= 0) continue;
      BASE = new DOMMatrix().translate(ox, oy).multiply(G);
      c.save(); c.setTransform(BASE); c.globalAlpha = al; SHOT_NOW = L.S.id;
      window.__FRAME.shots.push(L.S.id); window.__FRAME.base[L.S.id] = mx(BASE);
      (L.fn || stub)(c, t, L.S);
      c.restore(); SHOT_NOW = null;
      c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; c.filter = 'none';
    }
    BASE = G;
  }

  // 运动模糊：快门内取多个子帧平均；子帧不跨过硬切点（镜头边界里没有通用转场的那些 + CUTS）。
  // 循环片（project.json 的 "loop": true）：首尾不是硬切点，子帧按 t mod total 取，第 0 帧的模糊会采到上一圈末尾，首尾相接才逐像素一致；
  // render(t) 本身也按 total 取模，所以 render(total) 等于 render(0)。镜头里的运动用 springLoop 这类周期函数写，tools/loopcheck.py 检查接缝。
  // 采样数按画面变化自动定（固定的少量采样在快速平移、滚动转场里会把同一段字画成几份错开的清晰副本）：
  //   1. 先画快门中点 t 和快门末端，缩到 1/MB_PROBE 尺寸比较；变化折算到整个快门仍小于 MB_THR：画面没在动，只用 t 这一帧。
  //   2. 否则按梯形规则在快门内等距取点、逐级加倍（1 → 2 → 4 …，每级只补上一级的中点，已画的子帧都用上）：至少到 samples
  //      （向上取 2 的幂，最少 4；FAST 登记的段落用它给的数），之后每加倍一次比较新旧两级的累加结果，差小于 MB_THR 或到 max 就停。
  //   锚点表等登记取快门中点 t 那一张子帧。每帧的采样数累加进 window.__MBSTAT = {frames, samples_total, max_used, draws_total}。
  // 判据：两张图缩到 1/MB_PROBE 尺寸的灰度（0–255），切成 MB_TILE × MB_TILE 的小块（1/8 尺寸下 8 × 8 = 原图 64 × 64 像素）求平均差，取最大的
  // 那块。按小块取最大，是因为重影只出现在动的那一小片（一行字、一张卡片），整帧平均会被静止的大片背景冲淡。
  const MB_PROBE = 8, MB_TILE = 8;
  const MB_THR = 1.5;              // 灰度平均差（0–255）：小于它，两张图在最差的那一小块里也只差约 0.6%，多采样看不出区别（在快速平移、滚动转场的实际片段上标定）
  const LOOP = !!PROJECT.loop, TOT = TL.total, wrapT = t => ((t % TOT) + TOT) % TOT;
  const MB = Object.assign({ samples: 1, shutter: 0.5, max: 128 }, PROJECT.motion_blur || {});
  const pow2 = n => { let p = 1; while (p < n) p *= 2; return p; };
  const MB_MAX = Math.max(4, pow2(Math.max(1, MB.max | 0) + 1) / 2);      // 不超过 max 的最大 2 的幂
  const HARD = [...new Set([...ORDER.filter((s, i) => i > 0 && !trOf(i - 1)).map(s => s.t0), ...CUTS])].filter(e => e > 1e-9 && e < TOT - 1e-9).sort((x, y) => x - y);
  const segOf = t => {
    let lo = null, hi = null;
    for (const e of HARD) { if (e <= t + 1e-9) lo = e; else { hi = e; break; } }
    if (!LOOP) return [lo ?? 0, hi ?? TOT];
    return [lo ?? (HARD.length ? HARD[HARD.length - 1] - TOT : -Infinity), hi ?? (HARD.length ? HARD[0] + TOT : Infinity)];   // 首尾同属一段：跨过接缝
  };
  const mkcv = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d', { alpha: false })]; };
  const [acc, actx] = mkcv(W, H), [tmp, tctx] = mkcv(W, H), [mcv, mctx] = mkcv(W, H);    // 累加结果、快门中点那张子帧、快门起点那张子帧
  // 读回小图：先在 GPU 画布上逐级对半缩小（每级双线性正好是 2 × 2 平均，等于按块求平均，细笔画不会漏掉），最后一级缩进可读的小画布，
  // 两张图并排、一次 getImageData 读完（每次读回都要等 GPU 画完，次数越少越快）。不要直接 imageSmoothingQuality = 'high' 缩 8 倍：
  // 可读画布在 CPU 上，高质量缩小一张 1080p 要约 6 毫秒；也不要从可读画布以外的画布 getImageData：Chrome 会把它转成 CPU 画布，之后每笔都变慢。
  const SW = Math.max(8, Math.round(W / MB_PROBE)), SH = Math.max(8, Math.round(H / MB_PROBE));
  const sctx = (() => { const c = document.createElement('canvas'); c.width = SW * 2; c.height = SH; return c.getContext('2d', { alpha: false, willReadFrequently: true }); })();
  const HALF = [];                                                         // 1/2、1/4 …… 直到比 SW 大不到两倍
  for (let w = W, h = H; w / 2 >= SW * 1.5; ) { w = Math.round(w / 2); h = Math.round(h / 2); const c = mkcv(w, h); c[1].imageSmoothingQuality = 'low'; HALF.push(c); }
  function shrink(src, dx) {
    let s = src; for (const [c, g] of HALF) { g.drawImage(s, 0, 0, c.width, c.height); s = c; }
    sctx.drawImage(s, dx, 0, SW, SH);
  }
  function grayPair(a, b) {
    sctx.setTransform(1, 0, 0, 1, 0, 0); sctx.globalAlpha = 1; sctx.imageSmoothingQuality = 'low'; shrink(a, 0); shrink(b, SW);
    const d = sctx.getImageData(0, 0, SW * 2, SH).data, ga = new Float32Array(SW * SH), gb = new Float32Array(SW * SH);
    for (let y = 0, j = 0; y < SH; y++) for (let x = 0; x < SW; x++, j++) {
      const i = (y * SW * 2 + x) * 4, k = i + SW * 4;
      ga[j] = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]; gb[j] = 0.299 * d[k] + 0.587 * d[k + 1] + 0.114 * d[k + 2];
    }
    return [ga, gb];
  }
  function tileDiff(a, b) {                                               // 小块平均差的最大值
    let best = 0;
    for (let ty = 0; ty < SH; ty += MB_TILE) for (let tx = 0; tx < SW; tx += MB_TILE) {
      let s = 0, n = 0; const y1 = Math.min(SH, ty + MB_TILE), x1 = Math.min(SW, tx + MB_TILE);
      for (let y = ty; y < y1; y++) for (let x = tx, i = y * SW + tx; x < x1; x++, i++) { s += Math.abs(a[i] - b[i]); n++; }
      if (s / n > best) best = s / n;
    }
    return best;
  }
  const blend = (dst, src, a) => { dst.setTransform(1, 0, 0, 1, 0, 0); dst.globalCompositeOperation = 'source-over'; dst.filter = 'none'; dst.globalAlpha = a; dst.drawImage(src, 0, 0); dst.globalAlpha = 1; };
  // 新一级的 n 张子帧两两对半合并（像二进制计数），每张权重都是 1/n，每层只有半个灰阶的舍入。子帧直接画进栈里的画布，不另外拷贝。
  // 不用 alpha = 1/(k+1) 逐张叠加：8 位画布上 k 大时，和当前平均相差不到 (k+1)/2 个灰阶的子帧会被整个舍掉，采样越多越不准。
  const POOL = [];
  function meanOf(times) {                                                 // times 的长度是 2 的幂；返回装着平均结果的画布
    const lv = [];
    for (const ti of times) {
      const j = lv.length; if (!POOL[j]) POOL[j] = mkcv(W, H);
      frame(POOL[j][1], ti); lv.push(0);
      while (lv.length > 1 && lv[lv.length - 1] === lv[lv.length - 2]) { const k = lv.length - 1; blend(POOL[k - 1][1], POOL[k][0], 0.5); lv.pop(); lv[k - 1]++; }
    }
    return POOL[0][0];
  }
  const MBSTAT = window.__MBSTAT = { frames: 0, samples_total: 0, max_used: 0, draws_total: 0 };

  const REC = ['__ANCHORS', '__LINKS', '__ACTS', '__CAMS', '__GLOBAL', '__FRAME', '__TEXTS', '__SUBS'];   // 每帧重建的登记表
  function blurred(t) {
    const fast = FAST.find(([a, z]) => t >= a && t < z);
    const nMin = Math.min(MB_MAX, pow2(Math.max(4, (fast ? fast[2] || 16 : MB.samples) | 0)));
    const [lo, hi] = segOf(t), span = MB.shutter / FPS;
    const at = u => { const ti = clamp(t + (u - 0.5) * span, lo, hi - 1e-5); return LOOP ? wrapT(ti) : ti; };   // u = 0..1 快门内的位置
    frame(tctx, t); const keep = REC.map(k => window[k]);
    frame(actx, at(1));
    const [gC, gB] = grayPair(tmp, acc);
    let n = 1, draws = 2, out = tmp;
    if (tileDiff(gC, gB) * 2 >= MB_THR) {                                 // 半个快门的变化 × 2 ≈ 整个快门的变化
      frame(mctx, at(0)); draws++; blend(actx, mcv, 0.5);                  // 梯形规则 1 段：两端各一半
      blend(actx, tmp, 0.5); n = 2;                                        // 2 段：补上中点 t
      let d = Infinity;
      while (n < nMin || (d >= MB_THR && n < MB_MAX)) {
        const M = meanOf(Array.from({ length: n }, (_, k) => at((2 * k + 1) / (2 * n)))); draws += n;
        if (n * 2 >= nMin) { const [gT, gM] = grayPair(acc, M); d = tileDiff(gM, gT) / 2; }   // 新旧两级之差 = (新中点的平均 − 旧结果) / 2
        blend(actx, M, 0.5); n *= 2;
      }
      out = acc;
    }
    REC.forEach((k, j) => { window[k] = keep[j]; });
    blend(ctx, out, 1);
    const used = n === 1 ? 1 : n + 1;
    MBSTAT.frames++; MBSTAT.samples_total += used; MBSTAT.draws_total += draws; if (used > MBSTAT.max_used) MBSTAT.max_used = used;
  }
  async function render(t) {
    if (LOOP) t = wrapT(t);
    if (window.bgAt) await window.bgAt(t);
    if (window.__MB_OFF) frame(ctx, t); else blurred(t);
    T_NOW = t;
    if (window.STYLE && STYLE.overlay) { BASE = new DOMMatrix(); STYLE.overlay(ctx, t, ORDER.find(s => t >= s.t0 && t < s.t1) || ORDER[ORDER.length - 1]); }
    _subsDraw(ctx, t);                                        // 字幕层：在镜头和 overlay 之上、后期层之下，屏幕坐标，不受转场位移和运动模糊影响
    postFX(ctx, t, Math.round(t * FPS));
  }
  // 单独画一个镜头，返回那一刻 textBlock 的登记（同框换句用）。画在一块很小的画布上，不影响这一帧的画面、BASE 和各项登记。
  const BYID = Object.fromEntries(LIST.map(L => [L.S.id, L])), [, pctx] = mkcv(8, 8);
  window.__probeShot = function (id, tt) {
    const L = BYID[id]; if (LOOP) tt = wrapT(tt);
    if (!L || !L.fn || tt < L.a || tt >= L.z) return [];
    const keep = BASE, kR = REC.map(k => window[k]), kS = SHOT_NOW, kT = T_NOW;
    try {
      window.__ANCHORS = {}; window.__LINKS = []; window.__ACTS = []; window.__CAMS = {}; window.__TEXTS = [];
      BASE = new DOMMatrix(); T_NOW = tt; SHOT_NOW = id;
      pctx.setTransform(1, 0, 0, 1, 0, 0); pctx.globalAlpha = 1; pctx.save();
      try { _tbProbe(() => L.fn(pctx, tt, L.S)); } catch (e) { return []; } finally { pctx.restore(); }
      return window.__TEXTS;
    } finally { BASE = keep; REC.forEach((k, j) => { window[k] = kR[j]; }); SHOT_NOW = kS; T_NOW = kT; }
  };
  // 本片任意时刻的一帧（不含后期层），缩到 w 宽，返回 canvas：讲解片回顾前面的画面、画中画、把成片的某一帧当素材展示时用。
  // 用法：img(ctx, frameAt(7.3, 640), x, y, w, h)。结果按 (时刻, 宽度) 缓存；在画中画里再调用 frameAt 只得到一块底色，不会无限套娃。
  const _FA = new Map(); let _faDepth = 0, _faCv = null;
  window.frameAt = function (tt, w = 480) {
    const key = tt.toFixed(3) + '@' + w; if (_FA.has(key)) return _FA.get(key);
    const h = Math.round(w * H / W), out = document.createElement('canvas'); out.width = w; out.height = h;
    const g = out.getContext('2d', { alpha: false });
    if (_faDepth > 0) { g.fillStyle = COL.bg; g.fillRect(0, 0, w, h); return out; }
    if (!_faCv) { _faCv = document.createElement('canvas'); _faCv.width = W; _faCv.height = H; }
    const fc = _faCv.getContext('2d', { alpha: false }), keep = BASE, kR = REC.map(k => window[k]), kS = SHOT_NOW, kT = T_NOW; _faDepth++;
    try {
      frame(fc, LOOP ? wrapT(tt) : tt);
      if (window.STYLE && STYLE.overlay) { BASE = new DOMMatrix(); STYLE.overlay(fc, tt, ORDER.find(s => tt >= s.t0 && tt < s.t1) || ORDER[ORDER.length - 1]); }
    } finally { _faDepth--; BASE = keep; REC.forEach((k, j) => { window[k] = kR[j]; }); SHOT_NOW = kS; T_NOW = kT; }   // 画中画里的登记不算进这一帧
    g.drawImage(_faCv, 0, 0, w, h);
    if (_FA.size > 120) _FA.delete(_FA.keys().next().value);
    _FA.set(key, out); return out;
  };
  window.render = render;
  window.__info = { W, H, FMT, total: TL.total, fps: FPS, shots: ORDER.map(s => s.id), drawn: Object.keys(SHOT) };
  window.__ready = true;
})().catch(e => { console.error('启动失败：' + (e && e.stack || e)); window.__error = String(e && e.message || e); });
