/* =========================================================
   examples/promo_beats/shots_demo.js —— 8 秒、120 BPM 的节拍片示例（16 拍：钩子 4 拍、展示 4 拍、加速 3.5 拍 + 空拍半拍、drop 和落版 4 拍）
   用法：把本目录的 shots_demo.js 复制到 web/，project.json 用 examples/promo_beats/project.json，运行 python3 tools/timeline.py。
   示例的配色是示例自己的选择（深色底、橙色主角），片子的配色在方案里按题材和观众定，写进 project.json 的 theme.colors。
   示范的做法（见 references/promo.md）：
     1. 主角元素贯穿全片：一个橙色圆点。开场弹跳 → 冲进按钮（匹配转场）→ 变成卡片上的光标 → 收缩成一点 → drop 炸开 → 落成句号。
     2. 每一拍都有事发生：用 b(n) 取第 n 拍的时刻，动作都落在拍上或半拍上。
     3. 转场写在镜头里：相邻镜头用 pre/post 重叠，承接的是同一个元素，没有淡化。
     4. drop（第 12 拍）是全片最大的动作：砸字、震动、闪光；之前半拍是空拍（全黑）。
     5. 音效写在文件顶层，时刻与画面用同一个表达式。
     6. 背景由 main.js 每帧先画（theme.colors.bg），镜头里不铺底，重叠转场时两个镜头都看得见。
        只有要盖住上一个镜头的时候才在镜头里铺底（见 S02）。
     7. 标题和落版用 textBlock：给一块区域，字号由区域定，横版、竖版不用各算一遍；落版的句号位置从返回的字框算出来（S04）。
   这些只是一个起点：换掉内容、配色、节奏，不要照搬版式。
   ========================================================= */
'use strict';
(function () {
  const DOT = COL.acc;
  // 版面：横版左右排，竖版上下排。位置都按 W、H、U 写，同一套镜头出多个画幅（render.py --format all）
  const L = PORTRAIT
    ? { btn: [W * 0.5, H * 0.66], card: [W * 0.5, H * 0.62], cardRy: -18, word: [W * 0.5, H * 0.28], wordAlign: 'center' }
    : { btn: [W * 0.70, H * 0.62], card: [W * 0.62, H * 0.52], cardRy: -28, word: [140 * U, H * 0.56], wordAlign: 'left' };
  // 主角圆点在全片的位置与半径：几段弹簧叠加，结果只由 t 决定
  const TITLE = split(safeBox(), 'col', [2, 3])[0];
  const dotY = t => H * 0.5 - 220 * U * Math.abs(Math.sin(Math.PI * clamp(beatOf(t), 0, 3))) * (1 - clamp(beatOf(t) / 3));

  // ---------------------------------------------------------------- S01 钩子（b0–b4）：圆点每拍弹一次，越弹越低；标题逐字升起
  EV(b(0), 'pop'); EV(b(1), 'pop'); EV(b(2), 'pop'); EV(b(3.5), 'whoosh');
  SHOT.S01 = {
    post: 0.35, draw(ctx, t, S) {
      screen(ctx);
      const squash = 1 + 0.25 * Math.exp(-((beatOf(t) % 1) * BEAT) / 0.06) * (beatOf(t) < 3);
      // 第 3.5 拍起镜头冲向按钮：用 cam 推近
      const push = E.in3(prog(t, b(3.5), b(4) - b(3.5)));
      cam(ctx, lerp(W / 2, L.btn[0], push), lerp(H / 2, L.btn[1], push), 1 + 5 * push);
      // 第一帧就有字（at 早于镜头起点）：缩略图和自动播放的首帧就是它。区域是安全区上面五分之二，竖版时字号自动变小
      textBlock(ctx, 'Made with code.', TITLE, { role: 'title', weight: 800, max: 150 * U, align: 'center', valign: 'middle', lines: 1, t, at: S.t0 - 0.15 });
      // 按钮：第 3 拍出现在右侧
      const ba = spring(t - b(3), 3, 0.6);
      if (ba > 0) {
        ctx.save(); ctx.globalAlpha *= clamp(ba);
        ctx.translate(L.btn[0], L.btn[1]); ctx.scale(ba, ba);
        rrect(ctx, -150 * U, -48 * U, 300 * U, 96 * U, 48 * U); ctx.fillStyle = COL.ink; ctx.fill();
        txt(ctx, 'Start', 0, 14 * U, { font: F.b(40 * U, 700), color: COL.bg, align: 'center' });
        ctx.restore();
      }
      // 圆点
      const go = E.inOut3(prog(t, b(3), BEAT)), x = lerp(W / 2, L.btn[0], go), y = beatOf(t) < 3 ? dotY(t) : lerp(H * 0.5, L.btn[1] - 90 * U, go);
      ctx.save(); ctx.translate(x, y + 90 * U); ctx.scale(squash, 1 / squash);
      ctx.beginPath(); ctx.arc(0, 0, 36 * U, 0, Math.PI * 2); ctx.fillStyle = DOT; ctx.fill(); ctx.restore();
      // 冲进按钮的最后 0.35 秒：橙色铺满画面（匹配转场的前半段）
      const flood = E.in2(prog(t, S.t1 - 0.12, 0.47));
      if (flood > 0) { screen(ctx); ctx.beginPath(); ctx.arc(L.btn[0], L.btn[1], Math.hypot(W, H) * flood, 0, Math.PI * 2); ctx.fillStyle = DOT; ctx.fill(); }
    }
  };

  // ---------------------------------------------------------------- S02 展示（b4–b8）：橙色收缩成卡片上的光标；透视卡片每拍换一个词
  const WORDS = ['Timing.', 'Springs.', 'Type.', 'Rhythm.'];
  WORDS.forEach((w, i) => EV(b(4 + i), 'tick', { n: i }));
  // 卡片贴图：用离屏画布现画一张「界面截图」（真实片子里换成 assets.py 截的图：img: 'shot_app'）
  const UI = document.createElement('canvas'); UI.width = 1200; UI.height = 760;
  (window.INIT = window.INIT || []).push(async () => {
    const g = UI.getContext('2d');
    g.fillStyle = '#16181D'; g.fillRect(0, 0, 1200, 760);
    g.fillStyle = '#23262E'; g.fillRect(0, 0, 1200, 64);
    ['#FF5F57', '#FEBC2E', '#28C840'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(36 + i * 28, 32, 9, 0, 7); g.fill(); });
    for (let i = 0; i < 6; i++) { g.fillStyle = i === 2 ? COL.acc : '#2E323B'; g.fillRect(60, 120 + i * 96, i === 2 ? 520 : 300 + (i * 97) % 380, 40); }
    g.fillStyle = '#2E323B'; g.fillRect(700, 120, 440, 560);
  });
  SHOT.S02 = {
    pre: 0.12, draw(ctx, t, S) {
      screen(ctx); fillBg(ctx, COL.bg);                                // 有意铺底：盖住 S01 还在扩张的橙色，只露出正在收缩的圆
      const shrink = E.out3(prog(t, S.t0 - 0.12, 0.45));                 // 橙色从满屏收缩成光标（匹配转场的后半段）
      const tilt = springTo(t, [[S.t0, 0], [b(5), 1], [b(6), 2], [b(7), 3]], 2.4, 0.9);   // 阻尼接近 1：每拍转一格就停稳，不来回晃
      const [cx, cy] = L.card;
      GL3D.card(ctx, { img: UI, x: cx, y: cy, w: 1200 * U, h: 760 * U, ry: L.cardRy + tilt * 6, rx: 10 - tilt * 2, r: 22 * U,
        shadow: 0.9, border: 0.25, sheen: 0.5, sheenPos: lerp(-0.6, 1.8, prog(t, b(6), BEAT * 1.5)), a: clamp(shrink * 1.4) });
      // 左侧换词：每拍一个，旧词向上收走、新词弹起
      rollWords(ctx, WORDS.map((s, i) => ({ s, t: b(4 + i), colors: colorRange(s, [[s.length - 1, s.length, COL.acc]]) })), t, L.word[0], L.word[1],
        { font: F.d(170 * U, 800), size: 170 * U, align: L.wordAlign, z: 0.85 });   // 大字换词不回弹：回弹的大字整屏上下晃
      // 光标：钉在卡片上，每拍点一下
      const [px, py] = GL3D.uv(ctx, { x: cx, y: cy, w: 1200 * U, h: 760 * U, ry: L.cardRy + tilt * 6, rx: 10 - tilt * 2 }, 0.25 + 0.05 * tilt, 0.32 + 0.1 * (tilt % 2));
      const click = 1 - 0.25 * Math.exp(-((beatOf(t) % 1) * BEAT) / 0.08);
      const r = lerp(Math.hypot(W, H), 18 * U * click, shrink);
      ctx.save(); ctx.setTransform(BASE); ctx.beginPath(); ctx.arc(lerp(L.btn[0], px, shrink), lerp(L.btn[1], py, shrink), r, 0, Math.PI * 2); ctx.fillStyle = DOT; ctx.fill(); ctx.restore();
    }
  };

  // ---------------------------------------------------------------- S03 加速（b8–b11.5）+ 空拍（b11.5–b12）：网格加密、镜头推近、抖动增大，最后全黑
  for (let i = 0; i < 7; i++) EV(b(8 + i * 0.5), 'tick', { n: i + 4 });
  EV(b(11.5), 'riser', { dur: b(11.5) - b(10) });                  // riser 对准结尾：t 是冲到顶的那一刻，声音从 t - dur 开始
  SHOT.S03 = function (ctx, t, S) {
    screen(ctx);
    if (t >= b(11.5)) return;                                            // 空拍：什么都不画，只剩底色，让 drop 有对比
    const u = prog(t, S.t0, b(11.5) - S.t0), [hx, hy] = handheld(t, 4 + 18 * u * u, 3);
    cam(ctx, W / 2 + hx, H / 2 + hy, 1 + 0.6 * E.in2(u));               // 越来越快地推近
    // 网格每半拍加一行一列，新线条用强调色亮一下再退成灰：每半拍都有看得见的新东西
    const half = Math.floor((beatOf(t) - 8) * 2), n = half + 2;
    const gw = Math.min(W, H) * 0.8, gh = gw, x0 = W / 2 - gw / 2, y0 = H / 2 - gh / 2;
    for (let i = 0; i <= n; i++) {
      const born = b(8 + Math.max(0, i - 2) * 0.5), hot = decay(t, born, 0.18);
      ctx.strokeStyle = mixHex(COL.ink2, COL.acc, i >= n - 1 ? hot : 0); ctx.globalAlpha = 0.35 + 0.65 * (i >= n - 1 ? hot : 0); ctx.lineWidth = (2 + 3 * (i >= n - 1 ? hot : 0)) * U;
      ctx.beginPath(); ctx.moveTo(x0 + gw * i / n, y0); ctx.lineTo(x0 + gw * i / n, y0 + gh); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x0, y0 + gh * i / n); ctx.lineTo(x0 + gw, y0 + gh * i / n); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    // 圆点每半拍跳到一个新的格点，最后一拍回到中心
    const R = rng(11), pts = []; for (let i = 0; i < 8; i++) pts.push([Math.floor(R() * 5) - 2, Math.floor(R() * 5) - 2]);
    const k = clamp(half, 0, 6), [gx, gy] = beatOf(t) >= 11 ? [0, 0] : pts[k], step = gw / 5;
    const mv = spring(t - b(8 + half * 0.5), 4, 0.7), [px, py] = beatOf(t) >= 11 || k === 0 ? [0, 0] : pts[k - 1];
    const dx = W / 2 + lerp(px, gx, mv) * step, dy = H / 2 + lerp(py, gy, mv) * step;
    ctx.beginPath(); ctx.arc(dx, dy, 26 * U * (1 - 0.5 * u), 0, Math.PI * 2); ctx.fillStyle = DOT; ctx.fill();
  };

  // ---------------------------------------------------------------- S04 drop（b12）+ 落版：圆点炸开，砸字，最后圆点落成句号
  EV(b(12), 'impact', { size: 0.8 });            // drop 段起点自带镲和次低频，impact 叠在上面用 0.8
  SHAKES.push([b(12), 26, 0.12]); FLASH.push([b(12), 0.5, 0.06, '#FFFFFF']);   // 默认 light 模式：提亮砸下来的字，黑底不变灰
  CUTS.push(b(11.5), b(12));
  EV(b(14), 'pop');
  SHOT.S04 = function (ctx, t, S) {
    screen(ctx);
    const lt = enter(t, S.t0, 0.06), R = rng(7);        // drop 那一帧砸字已经起手：观众听到重拍时就看到字
    // 放射的碎片：每一片的方向和速度由种子决定
    for (let i = 0; i < 48; i++) {
      const ang = R() * Math.PI * 2, sp = (300 + R() * 900) * U, life = 0.5 + R() * 0.5, k = clamp(lt / life);
      if (k >= 1) continue;
      const d = sp * E.out3(k);
      ctx.globalAlpha = 1 - k; ctx.fillStyle = i % 5 ? DOT : COL.ink;
      ctx.beginPath(); ctx.arc(W / 2 + Math.cos(ang) * d, H / 2 + Math.sin(ang) * d, (10 + R() * 14) * U * (1 - k), 0, 7); ctx.fill();
    }
    ctx.globalAlpha = 1;
    cam(ctx, W / 2, H / 2, 1 + 0.03 * prog(t, S.t0, S.dur));            // 落位后缓推，不让画面停住
    // 砸字：右边留出句号的位置，字号由区域定（竖版自动变小）
    const M = textBlock(ctx, 'Motion', inset(safeBox(), [0, 100 * U, 0, 0]), { role: 'title', weight: 800, max: 220 * U, align: 'center', valign: 'middle', lines: 1,
      style: 'slam', charGap: 0.014, t, at: S.t0 - 0.06 });
    // 句号：第 14 拍从上方落到字尾，位置和大小从字框算出来
    const dk = spring(t - b(14), 2.6, 0.45), ln = M.lines[0];
    if (dk > 0) { ctx.beginPath(); ctx.arc(ln.x + ln.w + M.size * 0.23, lerp(H * 0.1, ln.y - M.size * 0.09, dk), M.size * 0.12, 0, 7); ctx.fillStyle = DOT; ctx.fill(); }
  };
})();
