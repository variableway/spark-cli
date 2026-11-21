/* =========================================================
   examples/explainer_voice/shots_demo.js —— 讲解片示例「植物怎么喝水」（约 35 秒，配音驱动的时间轴）
   用法：本目录的 project.json → 工程根目录，vo.json → script/，shots_demo.js → web/；
         python3 tools/timeline.py --estimate（还没有配音时按音节估时）；合成配音后去掉 --estimate 重跑，画面自动对齐真实配音。
   示例的配色是示例自己的选择（浅色纸面），片子的配色在方案里按题材和观众定，写进 project.json 的 theme.colors。
   这个示例演示机制，不示范版式：
     1. 版面不手填坐标：split 把安全区分成「字」和「台」两块（横版左右、竖版上下），物件按自然尺寸画，fit 放进台子，主体占满分到的区域。
        project.json 加 formats 就能出竖版、方形，镜头代码不用改。
     2. 字用 textBlock：给一块区域，断行和字号由它定，字自动够大、不出框；\n 是想在哪断行就在哪断。
     3. 每个短句一个画面事件：act(t, ph(id, k), {name}) 返回 0..1，时长默认按短句长短算；name 是事件名，体检的对齐图上显示。
     4. 一个物件贯穿全片：同一棵树，每一步原理都是它的一个动作（根吸水、细管运水、叶子散水、水被拉上去）。
        主角物件登记进 PROP：PROP.tree 按自然尺寸画，PROP.tree.size 写尺寸；先用 tools/stills.py --props 单独画大检查，
        镜头里 prop(ctx, 'tree', STAGE, {...}) 放进台子，返回的 fit 结果交给 place() 在同一套坐标里画标尺、锚点这些附加的东西。
     5. 标注用锚点：画目标时 anchor() 登记，textBlock 的 o.anchor 登记标签，callout() 从标签画到目标，镜头推近时终点跟着走（S02、S03）。
     6. 图表用 chartScale：柱子、太阳、图钉都从同一份数据和同一个比例尺算出来，pin() 标出最大值（S05）。图里的数是示意值。
     7. 帧率 30（project.json 的 fps）：讲解片以图形和文字为主。
     8. 中英双语字幕：project.json 的 "subtitles": {"burn": true, "langs": ["zh", "en"]}，vo.json 每个镜头的 "en" 按短句一句一条。
        引擎在底部字幕带画字幕，safeBox() 自动让出这条带，镜头代码不用为字幕改任何东西。
   约定：SHOT.<id> = function (ctx, t, S) {...}，t 是全局秒，画面只由 t 算出；S = {t0, t1, dur, phrases}；EV() 写在文件顶层。
   ========================================================= */
'use strict';
(function () {
  // ---------------------------------------------------------------- 版面：一侧放字，一侧放物件
  const [SIDE, STAGE] = split(safeBox(), PORTRAIT ? 'col' : 'row', SQUARE ? [1, 1] : [2, 3], 48 * U);   // 方形的字那一侧窄，分一半
  const SC = [STAGE.x + STAGE.w / 2, STAGE.y + STAGE.h / 2];
  const look = (p, z) => [p[0] - (SC[0] - W / 2) / z, p[1] - (SC[1] - H / 2) / z, z];   // 推近时让 p 落在台子中央，字那一侧留给字
  const place = (ctx, f, draw) => { ctx.save(); ctx.translate(f.x, f.y); ctx.scale(f.s, f.s); draw(); ctx.restore(); };
  const to = f => (x, y) => [f.x + x * f.s, f.y + y * f.s];                              // 物件坐标 → 版面坐标

  // ---------------------------------------------------------------- 主角物件：一棵树，按自然尺寸 920 × 1015 画，登记进 PROP
  const TX = 460, GY = 755, TOP = 305, TW = 64;                                          // 树干中线、地面、树干顶、树干宽
  const CROWN = [[TX, 205, 190], [TX - 140, 280, 125], [TX + 140, 280, 125], [TX - 70, 120, 120], [TX + 75, 125, 115]];
  const ROOTS = [
    [[TX, GY], [TX - 60, GY + 70], [TX - 150, GY + 110]], [[TX, GY], [TX + 50, GY + 80], [TX + 140, GY + 120]],
    [[TX, GY], [TX - 5, GY + 100], [TX - 30, GY + 160]], [[TX - 20, GY + 10], [TX - 100, GY + 40], [TX - 210, GY + 50]],
    [[TX + 20, GY + 10], [TX + 100, GY + 35], [TX + 220, GY + 45]],
  ];
  const TUBES = [TX - 16, TX, TX + 16];
  const dot = (ctx, x, y, r, col, a = 1) => { if (a <= 0) return; ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); ctx.restore(); };
  const column = (ctx, u, a = 1) => { if (u <= 0 || a <= 0) return; const y = lerp(GY + 30, TOP - 40, u); ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = COL.water; ctx.fillRect(TX - 9, y, 18, GY + 30 - y); ctx.restore(); };
  const along = (pts, u) => {                                                            // 折线上按长度比例 u 取点
    let L = pathLen(pts) * clamp(u);
    for (let i = 1; i < pts.length; i++) { const [ax, ay] = pts[i - 1], [bx, by] = pts[i], d = Math.hypot(bx - ax, by - ay); if (L <= d) return [ax + (bx - ax) * L / d, ay + (by - ay) * L / d]; L -= d; }
    return pts[pts.length - 1];
  };
  // o.grow 0..1：根、树干、树冠依次长出（默认 1）；o.inside() 画在树干上、树冠下；o.crown 树冠颜色
  PROP.tree = function (ctx, t, o) {
    const grow = o.grow ?? 1, inside = o.inside, crown = o.crown || COL.leaf;
    ctx.fillStyle = COL.soil; ctx.fillRect(0, GY, 920, 260);
    ROOTS.forEach((r, i) => drawPath(ctx, r, E.out3(prog(grow, i * 0.04, 0.35)), { color: COL.trunk, lw: 7 }));
    const h = (GY - TOP + 40) * E.out3(prog(grow, 0.15, 0.4));
    ctx.fillStyle = COL.trunk; ctx.fillRect(TX - TW / 2, GY - h, TW, h);
    if (inside) inside();
    CROWN.forEach(([x, y, r], i) => { const s = E.out3(prog(grow, 0.45 + i * 0.06, 0.35)); if (s > 0) dot(ctx, x, y, r * s, crown); });
  };
  PROP.tree.size = [920, 1015];
  const TREE = fit(STAGE, ...PROP.tree.size, { align: 'bottom' }), TP = to(TREE);         // 镜头推近时要算树上某一点的位置
  function flow(ctx, x, y0, y1, t, a, o = {}) {                                          // 水沿竖线往上流：小点等距排开、匀速上移
    if (a <= 0) return;
    const gap = o.gap ?? 34, off = ((t * (o.speed ?? 70)) % gap + gap) % gap;
    for (let y = y0 - off; y > y1; y -= gap) dot(ctx, x, y, o.r ?? 5, COL.water, a * clamp((y0 - y) / 40) * clamp((y - y1) / 40));
  }
  function vapor(ctx, x, y, t, a, seed, o = {}) {                                        // 水汽：冒出、上升、变淡，周期循环
    if (a <= 0) return;
    const n = o.n ?? 3, rise = o.rise ?? 120, per = o.per ?? 1.6, ph0 = rng(seed)();
    for (let j = 0; j < n; j++) {
      const life = ((t / per + ph0 + j / n) % 1 + 1) % 1;
      dot(ctx, x + Math.sin(life * 5 + seed) * (o.sway ?? 8), y - life * rise, (o.r ?? 6) * (0.6 + life), COL.water, a * 0.6 * (1 - life) * clamp(life * 6));
    }
  }

  // ---------------------------------------------------------------- S01 问题：没有心脏，水怎么上到树梢
  SHOT.S01 = function (ctx, t, S) {
    const grow = act(t, ph('S01', 0), { name: '树长出来', lead: 1.0, dur: 1.6, ease: E.lin });   // 提前起手：片子第一帧就有内容
    const up = act(t, ph('S01', 1), { name: '水升到树梢', dur: 1.8, ease: E.inOut3 });
    const wet = E.inOut2(prog(t, ph('S01', 1) + 1.6, 0.8)), out = prog(t, S.t1 - 0.5, 0.4);       // 水到了树冠就变亮；切镜前字收走
    cam(ctx, W / 2, H / 2, lerp(1, 1.03, prog(t, S.t0, S.dur)));
    const f = prop(ctx, 'tree', STAGE, { align: 'bottom', grow, inside: () => column(ctx, up), crown: mixHex(COL.leaf, COL.wet, wet) });
    place(ctx, f, () => {
      if (up > 0 && out < 1) {                                                           // 高度标尺跟着水长上去
        const rx = TX + 290, ry = lerp(GY, 5, E.out3(clamp(up * 1.4)));
        ctx.save(); ctx.globalAlpha *= 1 - out; ctx.strokeStyle = COL.ink2; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(rx, GY); ctx.lineTo(rx, ry);
        ctx.moveTo(rx - 14, GY); ctx.lineTo(rx + 14, GY); ctx.moveTo(rx - 14, ry); ctx.lineTo(rx + 14, ry); ctx.stroke(); ctx.restore();
        textBlock(ctx, '几十米', { x: rx + 22, y: (GY + ry) / 2 - 60, w: 920 - rx - 22, h: 120 }, { role: 'label', valign: 'middle', alpha: (1 - out) * prog(t, ph('S01', 1) + 1.0, 0.4) });
      }
    });
    screen(ctx);
    const [qa, qb] = split(SIDE, 'col', [1, 1], 24 * U), q2 = '水怎么\n到树梢？';
    textBlock(ctx, '一棵树\n没有心脏', qa, { role: 'title', valign: 'bottom', t, at: ph('S01', 0) - 0.1, out });
    textBlock(ctx, q2, qb, { role: 'title', t, at: ph('S01', 1), out, colors: colorRange(q2, [[0, 1, COL.water]]) });
  };
  EV(ph('S01', 1) + 0.2, 'pluck', { n: 2 });

  // ---------------------------------------------------------------- S02 根和细管：镜头推近，标注跟着目标走
  SHOT.S02 = function (ctx, t, S) {
    const k0 = ph('S02', 0), k1 = ph('S02', 1), root = TP(TX - 60, GY + 40), tube = TP(TX, 600);   // 推向细管时对准点偏下：根尖和「根」的标注留在字幕带上方
    cam(ctx, ...camKeys([[S.t0, W / 2, H / 2, 1.03], [k0 + 0.1, W / 2, H / 2, 1.03], [k0 + 1.4, ...look(root, 2.0)],
                         [k1 + 0.1, ...look(root, 2.0)], [k1 + 1.5, ...look(tube, 1.5)]], t));
    const sip = act(t, k0, { name: '根吸水' }), rise = act(t, k1, { name: '细管运水', lead: 0.2 });
    const keep = 1 - E.inOut2(prog(t, S.t0 + 0.2, 0.9));                                 // 接住上一个镜头：水柱和变亮的树冠慢慢退回
    const f = prop(ctx, 'tree', STAGE, { align: 'bottom', crown: mixHex(COL.leaf, COL.wet, keep), inside: () => {
      column(ctx, 1, keep);
      TUBES.forEach((x, i) => { ctx.save(); ctx.globalAlpha *= rise; ctx.fillStyle = COL.dim; ctx.fillRect(x - 4, TOP - 30, 8, GY - TOP + 30); ctx.restore(); flow(ctx, x, GY + 10, TOP - 30, t + i * 0.13, rise); });
    } });
    place(ctx, f, () => {
      ROOTS.forEach((r, i) => { const pts = r.slice().reverse(); for (let j = 0; j < 3; j++) { const u = (t * 0.45 + j / 3 + i * 0.17) % 1, [x, y] = along(pts, u); dot(ctx, x, y, 5, COL.water, sip * clamp(u * 5) * clamp((1 - u) * 5)); } });
      const tip = ROOTS[0][2];
      anchor(ctx, 'root', tip[0] - 10, tip[1] - 10, 20, 20);                             // 目标：最左边那条根的根尖
      anchor(ctx, 'tubes', TX - 22, 435, 44, 220);                                       // 目标：树干里的细管
    });
    screen(ctx);
    const [la, lb] = split(SIDE, 'col', [1, 1], 24 * U);
    textBlock(ctx, '根', la, { role: 'title', valign: 'middle', t, at: k0 + 0.3, anchor: 'root.label' });
    callout(ctx, 'root', 'root.label', { elbow: 'h', p: E.inOut3(prog(t, k0 + 0.6, 0.6)), color: COL.ink2, lw: 3 * U });
    textBlock(ctx, '细管', lb, { role: 'title', valign: 'middle', t, at: k1 + 0.4, anchor: 'tubes.label' });
    callout(ctx, 'tubes', 'tubes.label', { p: E.inOut3(prog(t, k1 + 0.7, 0.5)), color: COL.ink2, lw: 3 * U });
  };
  EV(ph('S02', 0) + 0.6, 'tick', { n: 1 });
  EV(ph('S02', 1) + 0.7, 'tick', { n: 3 });

  // ---------------------------------------------------------------- S03 叶片背面的气孔：推近到一个气孔，水汽散出去
  const LEAFF = fit(STAGE, 1100, 640), LP = to(LEAFF);                                    // 叶片按自然尺寸 1100 × 640 画
  const LEAF = { x: 550, y: 320, len: 1000, wid: 300, ang: -0.32 };
  const leafPt = (s, v) => {                                                             // s 沿叶长 0..1，v 横向 -1..1 → 叶片坐标
    const lx = (s - 0.5) * LEAF.len, ly = v * LEAF.wid / 2 * Math.sin(Math.PI * s), c = Math.cos(LEAF.ang), sn = Math.sin(LEAF.ang);
    return [LEAF.x + c * lx - sn * ly, LEAF.y + sn * lx + c * ly];
  };
  const STOMA = (() => {                                                                 // 第 0 个是镜头要推近的那个；其余随机撒开，彼此不重叠
    const r = rng(11), out = [[0.56, 0.42]], far = (a, b) => Math.hypot(...[0, 1].map(i => leafPt(...a)[i] - leafPt(...b)[i])) > 70;
    for (let n = 0; out.length < 26 && n < 2000; n++) { const c = [0.12 + r() * 0.76, (r() * 2 - 1) * 0.8]; if (Math.abs(c[1]) > 0.12 && out.every(q => far(c, q))) out.push(c); }
    return out;
  })();
  function stoma(ctx, x, y, s) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(LEAF.ang); ctx.scale(s, s);
    ctx.fillStyle = COL.leaf; ctx.beginPath(); ctx.ellipse(0, 0, 16, 10, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = COL.ink; ctx.beginPath(); ctx.ellipse(0, 0, 9, 2.5, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }
  SHOT.S03 = function (ctx, t, S) {
    const k = [0, 1, 2].map(i => ph('S03', i)), s0 = LP(...leafPt(...STOMA[0]));
    cam(ctx, ...camKeys([[S.t0, W / 2, H / 2, 1.0], [k[1] + 0.1, W / 2, H / 2, 1.0], [k[1] + 1.5, ...look(s0, 3.0)], [S.t1, ...look(s0, 3.4)]], t));
    const g = act(t, k[0], { name: '翻到叶片背面', lead: 0.5, dur: 0.7 });
    const u = act(t, k[1], { name: '气孔逐个出现', lead: 0.3, dur: 1.0, ease: E.lin });   // 线性的局部时间，交给 stagger 排先后
    const va = act(t, k[2], { name: '水汽散出' });
    place(ctx, LEAFF, () => {
      ctx.save(); ctx.globalAlpha *= g; ctx.fillStyle = COL.leafBack; ctx.beginPath();
      for (let i = 0; i <= 40; i++) { const [x, y] = leafPt(i / 40, 1); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
      for (let i = 40; i >= 0; i--) { const [x, y] = leafPt(i / 40, -1); ctx.lineTo(x, y); }
      ctx.fill(); ctx.restore();
      drawPath(ctx, [leafPt(0, 0), leafPt(1, 0)], g, { color: COL.leaf, lw: 6 });
      const sp = stagger(u, STOMA.length, 0.02, { order: 'point', pos: STOMA.map(p => leafPt(...p)), from: leafPt(...STOMA[0]), dur: 0.4 });
      STOMA.forEach((p, i) => { const [x, y] = leafPt(...p); if (sp[i] > 0) stoma(ctx, x, y, sp[i]); vapor(ctx, x, y - 6, t, va * sp[i], i + 3, { rise: 46, r: 2.4, sway: 3 }); });
      const [sx, sy] = leafPt(...STOMA[0]); anchor(ctx, 'stoma', sx - 16, sy - 12, 32, 24);
    });
    screen(ctx);
    // 字那一侧压一层底色：推近后叶片铺满画面，字下面不让气孔透出来
    const sh = PORTRAIT ? ctx.createLinearGradient(0, SIDE.y0, 0, SIDE.y1 + 48 * U) : ctx.createLinearGradient(SIDE.x0, 0, SIDE.x1 + 48 * U, 0);
    sh.addColorStop(0, hexA(COL.bg, 0.9)); sh.addColorStop(0.8, hexA(COL.bg, 0.9)); sh.addColorStop(1, hexA(COL.bg, 0));
    ctx.fillStyle = sh; PORTRAIT ? ctx.fillRect(0, 0, W, SIDE.y1 + 48 * U) : ctx.fillRect(0, 0, SIDE.x1 + 48 * U, H);
    // 竖版的引线从「气孔」向下指到叶片：说明放在标签右边并排，引线才不会穿过说明
    const [h1, h2, h3] = PORTRAIT ? (([a, r]) => [a, ...split(r, 'row', [1, 2], 24 * U)])(split(SIDE, 'col', [2, 2], 24 * U)) : split(SIDE, 'col', [2, 1, 1], 24 * U);
    textBlock(ctx, '动力来自叶子', h1, { role: 'title', valign: 'middle', t, at: k[0] });
    textBlock(ctx, '气孔', h2, { role: 'title', color: COL.leaf, t, at: k[1] + 0.6, anchor: 'stoma.label' });
    callout(ctx, 'stoma', 'stoma.label', { aim: [0.5, 0.5], p: E.inOut3(prog(t, k[1] + 0.9, 0.5)), color: COL.ink, lw: 3 * U });
    textBlock(ctx, '水变成水汽，散出去', h3, { role: 'body', color: COL.ink2, t, at: k[2] });
  };
  EV(ph('S03', 1) + 0.9, 'pin', { n: 2 });

  // ---------------------------------------------------------------- S04 像吸管：叶子每散一次水，水柱就上一格（吸管按自然尺寸 440 × 1020 画）
  const STRAW = fit(STAGE, 440, 1020), X = 220, Y0 = 900, Y1 = 300, GAP = 44;
  const PUFFS = (() => { const out = []; for (let p = ph('S04', 0) + 0.4; p < SCN('S04').t1 - 0.6; p += 1.1) out.push(p); return out; })();
  SHOT.S04 = function (ctx, t, S) {
    const k = [0, 1, 2].map(i => ph('S04', i));
    const g = act(t, k[0], { name: '叶子和吸管出现', lead: 0.5 }), pull = act(t, k[1], { name: '箭头往上拉' }), hl = act(t, k[2], { name: '吸管亮起' });
    cam(ctx, ...camKeys([[S.t0, W / 2, H / 2, 1.0], [S.t1, ...look(to(STRAW)(X, 600), 1.08)]], t, E.inOut2));   // 整段缓推向吸管
    place(ctx, STRAW, () => {
      ctx.save(); ctx.globalAlpha *= g;
      ctx.fillStyle = COL.soil; ctx.fillRect(0, Y0, 440, 120);
      ctx.strokeStyle = mixHex(COL.ink2, COL.acc, hl); ctx.lineWidth = 3 + 4 * hl; rrect(ctx, X - 30, Y1, 60, Y0 - Y1 + 40, 10); ctx.stroke();
      ctx.fillStyle = COL.leaf; ctx.beginPath(); ctx.ellipse(X, Y1 - 60, 120, 44, -0.2, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
      let off = 0; for (const p of PUFFS) off += GAP * E.inOut3(prog(t, p, 0.45));      // 每次散水，水柱上移一格（单调，不回弹）
      ctx.save(); rrect(ctx, X - 26, Y1, 52, Y0 - Y1 + 36, 8); ctx.clip();
      for (let j = -12; j < 16; j++) { const y = Y0 + 10 - j * GAP - off; if (y > Y1 - 20 && y < Y0 + 60) dot(ctx, X, y, 15, COL.water, g); }
      ctx.restore();
      PUFFS.forEach(p => { const lt = t - p; if (lt > 0 && lt < 1.4) for (let j = 0; j < 3; j++) dot(ctx, X - 50 + j * 50, Y1 - 90 - lt * 120, 9 * (1 + lt), COL.water, 0.5 * (1 - lt / 1.4)); });
      drawPath(ctx, [[X + 110, Y0 - 60], [X + 110, Y1 + 80]], pull, { color: COL.acc, lw: 6, arrow: 24 });
    });
    screen(ctx);
    const [a, b2, c] = split(SIDE, 'col', [1, 1, 1], 16 * U), same = '就往上拉一点';     // sizeText：前两句按同一个字号排
    textBlock(ctx, '散掉一点水', a, { role: 'title', valign: 'bottom', sizeText: same, t, at: k[0] });
    textBlock(ctx, same, b2, { role: 'title', valign: 'middle', color: COL.water, t, at: k[1] });
    textBlock(ctx, '像用吸管喝水', c, { role: 'body', color: COL.ink2, t, at: k[2] });
  };
  PUFFS.forEach((p, i) => EV(p, 'tick_soft', { pitch: i % 3 }));

  // ---------------------------------------------------------------- S05 一天里的散水量：比例尺算出柱子、太阳和图钉
  const HOURS = [6, 8, 10, 12, 14, 16, 18], LOSS = [1, 3, 6, 9, 8, 5, 2];               // 示意值：每两小时散掉的水（相对量）
  const [HEAD, PLOT] = split(safeBox(), 'col', [1, 4], 32 * U);
  SHOT.S05 = function (ctx, t, S) {
    const k = [0, 1, 2].map(i => ph('S05', i));
    const su = act(t, k[0], { name: '太阳走过一天', dur: 2.6, ease: E.inOut2 }), pinP = act(t, k[1], { name: '图钉标出中午', dur: 0.7 }), sw = act(t, k[2] - 0.3, { name: '换成结论', dur: 0.3, ease: E.in2 });   // 旧标题先退完，新标题再在同一处升起，两行不叠
    screen(ctx);
    const C = chartScale({ data: LOSS, box: inset(PLOT, [110 * U, 60 * U, 70 * U, 60 * U]), min: 0, max: 10 }), bw = (C.x(1) - C.x(0)) * 0.62;
    const sunX = C.x(su * (LOSS.length - 1)), sunY = C.box.y0 - 50 * U - Math.sin(Math.PI * su) * 40 * U;   // 太阳的 x 用同一个比例尺
    dot(ctx, sunX, sunY, 34 * U, COL.sun, prog(t, S.t0 - 0.2, 0.4));
    ctx.fillStyle = COL.dim; ctx.fillRect(C.box.x0, C.base, C.box.x1 - C.box.x0, 3 * U);
    const bp = stagger(t - k[0] + 0.2, LOSS.length, 0.12, { dur: 0.5 });
    LOSS.forEach((v, i) => {
      const r = C.bar(i, bw), lit = clamp((su * (LOSS.length - 1) - i + 0.5) * 2);       // 太阳经过时柱子点亮
      ctx.fillStyle = mixHex(COL.dim, COL.water, lit); ctx.fillRect(r.x, C.base - r.h * bp[i], r.w, r.h * bp[i]);
    });
    [0, 3, 6].forEach(i => textBlock(ctx, HOURS[i] + ' 时', { x: C.x(i) - bw, y: C.base + 16 * U, w: 2 * bw, h: 54 * U }, { role: 'label', align: 'center', alpha: prog(t, S.t0, 0.4) }));
    pin(ctx, C, LOSS[3], { at: 3, label: '中午最多', p: pinP, color: COL.ink, font: F.d(40 * U, 600) });
    textBlock(ctx, '一天里，叶子散掉的水', HEAD, { role: 'title', valign: 'middle', lines: 1, t, at: k[0] - 0.2, out: sw });
    textBlock(ctx, '散得越多，喝得越快', HEAD, { role: 'title', valign: 'middle', lines: 1, t, at: k[2] });
  };
  EV(ph('S05', 1) + 0.35, 'pin', { n: 4 });

  // ---------------------------------------------------------------- S06 结论：回到整棵树，水被叶子拉上去
  SHOT.S06 = function (ctx, t, S) {
    const k = [0, 1].map(i => ph('S06', i));
    const fl = act(t, k[0], { name: '水往上流' }), ar = act(t, k[1], { name: '箭头指向叶子', lead: 0.3, dur: 1.0, ease: E.inOut3 });
    cam(ctx, W / 2, H / 2, lerp(1.06, 1.0, E.out2(prog(t, S.t0, S.dur))));
    const f = prop(ctx, 'tree', STAGE, { align: 'bottom', inside: () => TUBES.forEach((x, i) => flow(ctx, x, GY + 10, TOP - 20, t + i * 0.13, fl, { speed: 110 })) });
    place(ctx, f, () => {
      CROWN.forEach(([x, y, r], i) => vapor(ctx, x, y - r * 0.8, t, fl, 40 + i, { rise: 140, r: 8 }));
      drawPath(ctx, [[TX + 260, GY - 20], [TX + 260, 200]], ar, { color: COL.acc, lw: 6, arrow: 22 });
    });
    screen(ctx);
    const [a, b2] = split(SIDE, 'col', [1, 2], 24 * U), s = '靠叶子\n在上面拉';
    textBlock(ctx, '树喝水', a, { role: 'body', valign: 'bottom', color: COL.ink2, t, at: k[0] });
    textBlock(ctx, s, b2, { role: 'title', t, at: k[1], colors: colorRange(s, [[1, 3, COL.leaf]]) });
  };
  EV(ph('S06', 1), 'chord_hit', { chord: 0 });
})();
