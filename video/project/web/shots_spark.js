/* =========================================================
   shots_spark.js —— spark-cli 介绍片（约 50 秒，配音驱动）

   画面分工（按用户确认的方案）：
     · 真实录屏主线：spark --help / version / repo --help / skill --help 的**真实输出**，
       由 cli-intro-video skill 的 record_terminal.py 录成无损帧序列，画面里是命令真的敲出来、输出真的打印。
     · 代码动画做架构图与标注层：命令族树、共享配置、标注下划线与编号对应，全部用画布代码画。

   素材几何来自 web/img/<素材>/meta.json 的 cell 字段（scale 2 超采样后缩到 1250 宽）：
     行高 CH = 30.1871px，文本首行顶 TOP = 51.0204px，列宽 COLW = 13.1803px，文本左边距 PADX = 18.7075px。
     所以「第 k 行」在素材里的 y = TOP + k*CH，可以精确换算到画面坐标做标注。

   约定：SHOT.<id> = function (ctx, t, S) {...}，画面只由 t 算出；EV() 写在文件顶层。
   ========================================================= */
'use strict';
(function () {

  // ---------------------------------------------------------------- 素材几何与公共工具
  // 素材几何来自 web/img/<素材>/meta.json 的 cell 字段（录制时写下的真实网格）：
  //     行高 CH = 30.1871px，文本首行顶 TOP = 51.0204px，列宽 COLW = 13.1803px，文本左边距 PADX = 18.7075px。
  //     列宽**不是**「画幅宽 ÷ 列数」：素材文本区两侧留了内边距（1250px 里文字只占 1212.6px），
  //     用名义值会让裁剪框超出素材边界，浏览器只能横向压掉一截——字被拉宽，标注线也整体偏 3%。
  //     所以「第 c 列的文本」在素材里的 x = PADX + c*COLW，「第 k 行」的 y = TOP + k*CH。
  //     check_crop.py 会拿这些常量和 meta.json 逐个比对，对不上就拦下来。
  const CH = 30.1871, TOP = 51.0204, COLW = 13.1803, PADX = 18.7075;
  const B = safeBox();
  const WIDE = !PORTRAIT && !SQUARE;          // 16:9 横版构图；竖版和方形走竖排
  // 标题区高度：方形只有 1080 高，标题两行放 380 太高，标题下留给画面的空间被吃掉一大半
  const HEAD_H = (WIDE ? 190 : PORTRAIT ? 380 : 235) * U;

  // 每种画幅用不同的裁剪：横版能容下 92 列（字约 19px），竖版只容 58 列（字约 17px），
  // 列多了字就小到看不清。行数按「这一段里最长的一行」定，保证不会把字截断——
  // 竖版第 10 行是 72 列的 completion，说明放不进 58 列，所以竖版停在第 9 行。
  // 方版只留「命令 + 四条能力」六行，把画面下半场留给编号说明。
  const CARD = WIDE
    ? { help: [11, 92], version: [4, 56], hub_registry: [11, 84], hub_collections: [11, 84] }
    : SQUARE
      ? { help: [5, 58], version: [4, 56], hub_registry: [11, 82], hub_collections: [11, 78] }
      : { help: [9, 58], version: [4, 56], hub_registry: [11, 82], hub_collections: [11, 78] };

  // 真实输出行（标注层要指到具体哪一行，长度用来算下划线）
  const L_HELP = [
    '$ spark --help',
    'Spark is a CLI application that helps you:',
    '1. Update multiple git repositories to the latest version',
    '2. Scan, register, and clone projects with spark hub',
    '3. Execute custom scripts with automation',
    '',
    'Usage:',
    '  spark [command]',
    '',
    'Available Commands:',
    '  completion  Generate the autocompletion script for the specified shell',
    '  docs        Documentation management commands',
  ];
  const L_VER = [
    '$ spark version',
    'spark v0.4.0',
    '  commit:     28d3f41',
    '  build date: 2026-11-22T03:43:11Z',
  ];

  // 裁一段素材：行区间（闭）+ 列区间（闭）。返回裁剪参数和行列起点，标注层要用
  function crop(r0, r1, c0, c1) {
    const y0 = r0 === 0 ? 0 : TOP + r0 * CH;
    const y1 = TOP + (r1 + 1) * CH;
    const w = Math.min(PADX + (c1 - c0) * COLW, 1250 - c0 * COLW);
    return { s: [c0 * COLW, y0, w, y1 - y0], c0, r0 };
  }
  // 按来源尺寸等比放进区域
  function fitBox(box, cw, ch, align) {
    const s = Math.min(box.w / cw, box.h / ch);
    const w = cw * s, h = ch * s, a = align || '';
    const x = /left/.test(a) ? box.x : /right/.test(a) ? box.x + box.w - w : box.x + (box.w - w) / 2;
    const y = /top/.test(a) ? box.y : /bottom/.test(a) ? box.y + box.h - h : box.y + (box.h - h) / 2;
    return { x, y, w, h, s };
  }
  // 素材里某一行（从第 c 列起 n 个字符）在画面上的矩形
  function rowAt(d, c, k, n, c0) {
    const s = d.w / c.s[2], cc = c0 ?? c.c0;
    return {
      x: d.x + (PADX + (cc - c.c0) * COLW) * s,
      y: d.y + (TOP + k * CH - c.s[1]) * s,
      w: n * COLW * s,
      h: CH * s,
    };
  }
  // 画一张终端卡：裁剪 + 圆角 + 投影。
  // 卡片比裁剪出的图像高出一小截：最后一行文字不会贴着卡片底边（终端本身也有下边距）。
  function term(ctx, im, c, d, alpha) {
    if (!im) return;
    const BAND = 20 * U, H = d.h + BAND, a = alpha ?? 1;
    ctx.save(); ctx.globalAlpha *= a;
    ctx.shadowColor = 'rgba(0,0,0,0.47)'; ctx.shadowBlur = 60 * U * 0.85; ctx.shadowOffsetY = 24 * U * 0.85;
    ctx.fillStyle = COL.termBg; rrect(ctx, d.x, d.y, d.w, H, 14 * U); ctx.fill();
    ctx.restore();
    ctx.save(); ctx.globalAlpha *= a;
    img(ctx, im, d.x, d.y, d.w, d.h, { fit: 'fill', src: c.s, r: 14 * U });
    ctx.restore();
  }
  // 标注层：目标行下面一条强调线
  function underline(ctx, d, c, k, n, p, col) {
    if (p <= 0) return;
    const r = rowAt(d, c, k, n);
    ctx.save(); ctx.globalAlpha *= p;
    ctx.fillStyle = col || COL.acc;
    ctx.fillRect(r.x, r.y + r.h - 5 * U, r.w, 3.5 * U);
    ctx.restore();
  }
  // 标注层：编号徽章 + 文字
  function badge(ctx, x, y, n, p, col, size) {
    if (p <= 0) return;
    const s = size || 34 * U;
    ctx.save(); ctx.globalAlpha *= p;
    ctx.fillStyle = col || COL.acc;
    rrect(ctx, x, y, s, s, 9 * U); ctx.fill();
    ctx.restore();
    textBlock(ctx, String(n), { x, y, w: s, h: s }, { role: 'label', color: COL.bg, align: 'center', valign: 'middle', t: 0, alpha: p, size: Math.round(s * 0.7) });
  }

  // ---------------------------------------------------------------- S01 钩子：标题 + 终端真的敲出一行命令
  SHOT.S01 = function (ctx, t, S) {
    screen(ctx);
    const HEAD = { x: B.x, y: B.y, w: B.w, h: HEAD_H };
    const AREA = { x: B.x, y: B.y + HEAD_H + 26 * U, w: B.w, h: B.h - HEAD_H - 26 * U };

    const c = crop(0, CARD.help[0], 0, CARD.help[1]);
    const d = fitBox(AREA, c.s[2], c.s[3], 'top');
    const rise = E.out3(prog(t, S.t0 - 0.4, 0.9));   // 提前起手：第一帧画面上就有东西
    ctx.save(); ctx.translate(0, (1 - rise) * 46 * U); ctx.globalAlpha = rise;
    term(ctx, seqFrame('help', t - S.t0, 15), c, d);
    ctx.restore();

    const [h1, h2] = split(HEAD, 'col', [1, 1], 8 * U);
    textBlock(ctx, '每天重复十遍的命令', h1, { role: 'title', valign: 'bottom', t, at: ph('S01', 0) - 0.05, color: COL.ink, max: 88 * U });
    textBlock(ctx, '交给一个工具', h2, { role: 'title', valign: 'top', t, at: ph('S01', 1), color: COL.acc, max: 88 * U });
  };

  // ---------------------------------------------------------------- S02 它是什么：四件真本事，按终端里的编号一一对应
  SHOT.S02 = function (ctx, t, S) {
    const P = [0, 1, 2, 3, 4].map(i => ph('S02', i));
    screen(ctx);

    const HEAD = { x: B.x, y: B.y, w: B.w, h: HEAD_H };
    const AREA = { x: B.x, y: B.y + HEAD_H + 26 * U, w: B.w, h: B.h - HEAD_H - 26 * U };
    // 裁剪跟 S01 一致：S02 是接着这张卡往下打印的，换裁剪会让卡片在切点处变形
    const c = crop(0, CARD.help[0], 0, CARD.help[1]);
    const d = fitBox(AREA, c.s[2], c.s[3], 'top');
    // 接着 S01 往下播：S01 放完了输入和前几行输出，这里接着打印
    term(ctx, seqFrame('help', (SCN('S01').t1 - SCN('S01').t0) + (t - S.t0), 15), c, d);

    const [h1, h2] = split(HEAD, 'col', [1, 1], 8 * U);
    textBlock(ctx, 'spark 是给多仓库工作准备的', h1, { role: 'title', valign: 'bottom', t, at: P[0] - 0.1, color: COL.ink, max: 88 * U });
    textBlock(ctx, '命令行工具', h2, { role: 'title', valign: 'top', t, at: P[0] + 0.5, color: COL.acc, max: 88 * U });

    // 四条能力：终端里本来就是 1. 2. 3. 4.，编号和它一一对应
    const ITEMS = [
      { k: 2, n: L_HELP[2].length, lb: '批量更新仓库' },
      { k: 3, n: L_HELP[3].length, lb: '扫描登记与克隆项目' },
      { k: 4, n: L_HELP[4].length, lb: '执行自定义脚本' },
    ];
    // 横版：编号排在终端卡右侧。竖版和方版：排在卡片**下面**——卡片是满宽的，
    // 里面没有留白，排到卡里会盖住终端的字（方版还排不下，只能往下让）。
    const bs = WIDE ? 34 * U : PORTRAIT ? 40 * U : 34 * U;       // 徽章边长
    const ls = WIDE ? 26 * U : PORTRAIT ? 30 * U : 25 * U;       // 说明文字字号
    const cols = SQUARE ? 2 : 1;
    const listX = WIDE ? d.x + (58 / 92) * d.w + 34 * U : B.x;
    const listW = WIDE ? d.w * 0.34 : B.w;
    const listTop = WIDE ? d.y + d.h * 0.10 : d.y + d.h + (SQUARE ? 32 * U : 34 * U);
    const listRows = Math.ceil(ITEMS.length / cols);
    const rowH = WIDE ? d.h * 0.62 / ITEMS.length
      : SQUARE ? 104 * U
      : Math.min(92 * U, (B.y + B.h - 100 * U - listTop) / ITEMS.length);
    ITEMS.forEach((it, i) => {
      const p = E.out3(prog(t, P[i + 1], 0.5));
      if (p <= 0) return;
      underline(ctx, d, c, it.k, it.n, p);
      const col = i % cols, row = (i - col) / cols;
      const x = listX + col * (listW / cols);
      const y = listTop + row * rowH;
      badge(ctx, x, y, i + 1, p, null, bs);
      textBlock(ctx, it.lb, { x: x + bs + 14 * U, y: y - 4 * U, w: listW / cols - bs - 14 * U, h: bs + 8 * U }, { role: 'label', color: COL.acc, t: 0, alpha: p, valign: 'middle', size: ls });
    });

    // 「都在一棵命令树里」：标到 Available Commands 那一行（方版没露出这一行，就不标）
    const p5 = E.out3(prog(t, P[4], 0.5));
    if (p5 > 0 && !SQUARE) {
      underline(ctx, d, c, 9, L_HELP[9].length, p5, COL.acc2);
      const r = rowAt(d, c, 9, L_HELP[9].length);
      const box = WIDE
        ? { x: r.x + r.w + 34 * U, y: r.y, w: d.w * 0.5, h: 34 * U }
        : { x: B.x, y: listTop + listRows * rowH + 10 * U, w: B.w, h: 44 * U };
      textBlock(ctx, '一棵命令树，八个命令族', box, { role: 'label', color: COL.acc2, t: 0, alpha: p5, valign: 'middle', size: 26 * U });
    }
  };

  // ---------------------------------------------------------------- S03 一行命令问出版本
  SHOT.S03 = function (ctx, t, S) {
    screen(ctx);
    const HEAD = { x: B.x, y: B.y, w: B.w, h: HEAD_H };
    const AREA = { x: B.x, y: B.y + HEAD_H + 26 * U, w: B.w, h: B.h - HEAD_H - 26 * U };

    const c = crop(0, CARD.version[0], 0, CARD.version[1]);   // 版本输出本身就短，裁窄一点字更大
    const d = fitBox(AREA, c.s[2], c.s[3], 'top');
    term(ctx, seqFrame('version', t - S.t0, 15), c, d);

    const [h1, h2] = split(HEAD, 'col', [1, 1], 8 * U);
    textBlock(ctx, '版本、提交、构建时间', h1, { role: 'title', valign: 'bottom', t, at: ph('S03', 0) - 0.1, color: COL.ink, max: 88 * U });
    textBlock(ctx, '一行命令就问出来', h2, { role: 'title', valign: 'top', t, at: ph('S03', 3), color: COL.acc, max: 88 * U });

    // 竖版：卡片是又宽又矮的一条，下面补一个大号版本号撑住版面（方版高度不够，不加）
    if (PORTRAIT) {
      const vy = d.y + d.h + 70 * U;
      const pv0 = E.out3(prog(t, ph('S03', 0) + 0.35, 0.6));
      if (pv0 > 0) {
        textBlock(ctx, '当前版本', { x: B.x, y: vy, w: B.w, h: 46 * U }, { role: 'label', color: COL.ink2, t: 0, alpha: pv0, align: 'center', valign: 'middle', size: 28 * U });
        textBlock(ctx, 'v0.4.0', { x: B.x, y: vy + 50 * U, w: B.w, h: 130 * U }, { role: 'title', color: COL.acc, t: 0, alpha: pv0, align: 'center', valign: 'middle', size: 104 * U });
        textBlock(ctx, 'commit 28d3f41', { x: B.x, y: vy + 196 * U, w: B.w, h: 44 * U }, { role: 'label', color: COL.ink, t: 0, alpha: pv0, align: 'center', valign: 'middle', size: 28 * U });
        textBlock(ctx, 'build 2026-11-22', { x: B.x, y: vy + 244 * U, w: B.w, h: 44 * U }, { role: 'label', color: COL.ink2, t: 0, alpha: pv0, align: 'center', valign: 'middle', size: 26 * U });
      }
    }

    // 版本号上盖一个醒目的框
    const pv = E.out3(prog(t, ph('S03', 0), 0.5));
    if (pv > 0) {
      const r = rowAt(d, c, 1, 12);
      ctx.save(); ctx.globalAlpha *= pv;
      ctx.strokeStyle = COL.acc; ctx.lineWidth = 2.5 * U;
      rrect(ctx, r.x - 10 * U, r.y + 2 * U, r.w + 20 * U, r.h - 5 * U, 8 * U); ctx.stroke();
      ctx.restore();
    }
  };

  // ---------------------------------------------------------------- S04 再看两个：注册表管仓库、技能自动发现
  SHOT.S04 = function (ctx, t, S) {
    const P = [0, 1, 2, 3].map(i => ph('S04', i));
    const sw = E.inOut3(prog(t, P[2], 0.6));            // 第 2 句起换到 skill
    screen(ctx);

    const HEAD = { x: B.x, y: B.y, w: B.w, h: HEAD_H };
    const AREA = { x: B.x, y: B.y + HEAD_H + 26 * U, w: B.w, h: B.h - HEAD_H - 26 * U };

    // 两张卡用**同样的裁剪几何**：叠化时尺寸不变，只有内容换掉
    const cR = crop(0, CARD.hub_registry[0], 0, CARD.hub_registry[1]);
    const cS = crop(0, CARD.hub_collections[0], 0, CARD.hub_collections[1]);
    const dR = fitBox(AREA, cR.s[2], cR.s[3], 'top');
    const dS = fitBox(AREA, cS.s[2], cS.s[3], 'top');

    ctx.save(); ctx.globalAlpha *= (1 - sw);
    term(ctx, 'hub_registry-still', cR, dR);
    ctx.restore();
    ctx.save(); ctx.globalAlpha *= sw;
    term(ctx, 'hub_collections-still', cS, dS);
    ctx.restore();

    const [h1, h2] = split(HEAD, 'col', [1, 1], 8 * U);
    const o1 = prog(t, P[2] - 0.12, 0.22);            // 旧标题先退干净
    textBlock(ctx, '参考项目用注册表文件管', h1, { role: 'title', valign: 'bottom', t, at: P[0] - 0.1, out: o1, color: COL.ink, max: 88 * U });
    textBlock(ctx, '一份清单就能还原', h2, { role: 'title', valign: 'top', t, at: P[1], out: o1, color: COL.acc, max: 88 * U });
    const o2 = prog(t, P[3] + 0.6, 0.3);
    textBlock(ctx, '自己开发的应用登记进目录', h1, { role: 'title', valign: 'bottom', t, at: P[2] + 0.1, out: o2, color: COL.ink, max: 88 * U });
    textBlock(ctx, '和参考项目分开管', h2, { role: 'title', valign: 'top', t, at: P[3] + 0.05, out: o2, color: COL.acc, max: 88 * U });

    // 标注：注册表那一行、技能发现的那一行
    underline(ctx, dR, cR, 1, 64, E.out3(prog(t, P[0], 0.5)));
    underline(ctx, dS, cS, 1, 70, E.out3(prog(t, P[2], 0.5)));
  };

  // ---------------------------------------------------------------- S05 为什么用：代码动画画架构
  const FAMS = [
    ['git', '多仓库管理'], ['hub', '参考项目与应用两本目录'],
    ['magic', '系统工具'], ['script', '执行自定义脚本'],
    ['docs', '文档管理'], ['witr', '进程溯源'], ['version', '版本信息'],
    ['completion', 'Shell 补全'],
  ];
  SHOT.S05 = function (ctx, t, S) {
    const P = [0, 1, 2, 3, 4, 5].map(i => ph('S05', i));
    screen(ctx);

    const HEAD = { x: B.x, y: B.y, w: B.w, h: HEAD_H };
    const REST = { x: B.x, y: B.y + HEAD_H + 18 * U, w: B.w, h: B.h - HEAD_H - 18 * U };
    const [NODE, GRID, BOT] = split(REST, 'col', [1, 2.9, 1.35], 18 * U);
    const [CFGB, PROJ] = split(BOT, 'row', [1, 1], 22 * U);

    const [h1, h2] = split(HEAD, 'col', [1, 1], 6 * U);
    textBlock(ctx, '八个命令族', h1, { role: 'title', valign: 'bottom', t, at: P[0] - 0.1, color: COL.ink, max: 88 * U });
    textBlock(ctx, '共享同一份配置', h2, { role: 'title', valign: 'top', t, at: P[1], color: COL.acc, max: 88 * U });

    // 中心：spark。镜头一进来就在，切点不留空画面
    const NW = WIDE ? 340 * U : 280 * U, NH = 92 * U;
    const nx = NODE.x + (NODE.w - NW) / 2, ny = NODE.y + (NODE.h - NH) / 2;
    const gn = E.out3(prog(t, S.t0 - 0.35, 0.8));
    if (gn > 0) {
      ctx.save(); ctx.globalAlpha *= gn;
      ctx.fillStyle = COL.ink; rrect(ctx, nx, ny, NW, NH, 18 * U); ctx.fill();
      ctx.restore();
      textBlock(ctx, 'spark', { x: nx, y: ny, w: NW, h: NH }, { role: 'title', color: COL.bg, align: 'center', valign: 'middle', t: 0, alpha: gn, size: 46 * U });
    }

    // 命令族卡片：十个族逐个亮起来
    const cols = WIDE ? 4 : 2, rows = Math.ceil(FAMS.length / cols);
    const cells = grid(GRID, cols, rows, 16 * U);
    const sp = stagger(t - S.t0 + 0.25, FAMS.length, 0.07, { dur: 0.45 });
    FAMS.forEach((f, i) => {
      const c0 = cells[i], p = sp[i];
      if (p <= 0) return;
      ctx.save(); ctx.globalAlpha *= p;
      ctx.fillStyle = COL.bg; ctx.strokeStyle = COL.dim; ctx.lineWidth = 2 * U;
      rrect(ctx, c0.x, c0.y, c0.w, c0.h, 14 * U); ctx.fill(); ctx.stroke();
      ctx.restore();
      const two = c0.h >= 74 * U;          // 格子够高才放第二行说明，否则只留命令名
      textBlock(ctx, 'spark ' + f[0], { x: c0.x, y: c0.y + c0.h * 0.05, w: c0.w, h: two ? c0.h * 0.40 : c0.h * 0.90 }, { role: 'label', color: COL.ink, align: 'center', valign: 'middle', t: 0, alpha: p, size: two ? 31 * U : 36 * U });
      if (two) textBlock(ctx, f[1], { x: c0.x, y: c0.y + c0.h * 0.48, w: c0.w, h: c0.h * 0.44 }, { role: 'caption', color: COL.ink2, align: 'center', valign: 'middle', t: 0, alpha: p, size: 25 * U });
    });

    // 共享的一份配置
    const pc = E.out3(prog(t, P[1], 0.6));
    if (pc > 0) {
      ctx.save(); ctx.globalAlpha *= pc;
      ctx.fillStyle = hexA(COL.acc, 0.12); ctx.strokeStyle = COL.acc; ctx.lineWidth = 2 * U;
      rrect(ctx, CFGB.x, CFGB.y + CFGB.h * 0.14, CFGB.w, CFGB.h * 0.72, 14 * U); ctx.fill(); ctx.stroke();
      ctx.restore();
      textBlock(ctx, '~/.spark.yaml', { x: CFGB.x, y: CFGB.y + CFGB.h * 0.14, w: CFGB.w, h: CFGB.h * 0.72 }, { role: 'label', color: COL.acc, align: 'center', valign: 'middle', t: 0, alpha: pc, size: 32 * U });
    }

    // 同一条命令，在哪个项目里都一样；最后再多一个项目，呼应「到处都能用」
    const ps = E.out3(prog(t, P[2], 0.6));
    const PROJS = [['项目 A', 'spark git update'], ['项目 B', 'spark git update'], ['项目 C', 'spark git update']];
    if (ps > 0) {
      PROJS.forEach((r, i) => {
        const at = i < 2 ? P[2] + i * 0.18 : P[5];
        const p = E.out3(prog(t, at, 0.5));
        if (p <= 0) return;
        const y = PROJ.y + i * (PROJ.h / PROJS.length) + PROJ.h * 0.05;
        const h = PROJ.h / PROJS.length * 0.9;
        textBlock(ctx, r[0], { x: PROJ.x, y, w: PROJ.w * 0.26, h }, { role: 'label', color: COL.ink2, t: 0, alpha: p, valign: 'middle', size: 25 * U });
        textBlock(ctx, r[1], { x: PROJ.x + PROJ.w * 0.28, y, w: PROJ.w * 0.72, h }, { role: 'label', color: COL.ink, t: 0, alpha: p, valign: 'middle', size: 25 * U });
      });
    }
  };

  // ---------------------------------------------------------------- S06 速查与落版
  const QUICK = [
    ['spark git batch-clone', '克隆整个账号的仓库'],
    ['spark hub registry', '注册表管参考项目'],
    ['spark hub collections', '登记自己开发的应用'],
    ['spark magic clean', '清掉 node_modules'],
    ['spark magic flush-dns', '清 DNS 缓存'],
  ];
  SHOT.S06 = function (ctx, t, S) {
    const P = [0, 1, 2].map(i => ph('S06', i));
    screen(ctx);

    // 横版左右分栏；竖版和方形上下堆叠（窄栏放不下速查卡的两列）
    const STACK = !WIDE;
    let L, R, cardH, urlY;
    if (STACK) {
      L = { x: B.x, y: B.y, w: B.w, h: 330 * U };
      R = { x: B.x, y: B.y + 350 * U, w: B.w, h: B.h - 350 * U };
      cardH = R.h * 0.72; urlY = R.y + R.h * 0.77;
    } else {
      const sp = split(B, 'row', [1, 1.3], 44 * U); L = sp[0]; R = sp[1];
      cardH = R.h * 0.8; urlY = R.y + R.h * 0.82;
    }

    // 左：logo + 名字 + 一句话
    const logo = IMG['spark_mark'];
    const lgW = STACK ? 150 * U : L.w * 0.42;
    const lg = fitBox({ x: L.x, y: L.y, w: lgW, h: lgW * 1.05 }, 854, 897, 'left top');
    if (logo) {
      ctx.save(); ctx.globalAlpha *= E.out3(prog(t, S.t0 - 0.35, 0.9));
      img(ctx, logo, lg.x, lg.y, lg.w, lg.h, { fit: 'contain' });
      ctx.restore();
    }
    const nx = STACK ? lg.x + lg.w + 26 * U : L.x;
    const nw = STACK ? L.w - lg.w - 26 * U : L.w;
    const nm = { x: nx, y: STACK ? lg.y : lg.y + lg.h + 24 * U, w: nw, h: 110 * U };
    textBlock(ctx, 'spark', nm, { role: 'title', t, at: P[0] - 0.2, color: COL.ink, max: 96 * U });
    textBlock(ctx, '把每天重复的事，交给命令行', { x: nx, y: nm.y + nm.h, w: nw, h: 90 * U }, { role: 'body', t, at: P[1], color: COL.ink2 });

    // 右：速查卡
    const cBox = { x: R.x, y: R.y, w: R.w, h: cardH };
    ctx.save(); ctx.globalAlpha *= E.out3(prog(t, S.t0 - 0.2, 0.8));
    ctx.fillStyle = COL.ink; rrect(ctx, cBox.x, cBox.y, cBox.w, cBox.h, 18 * U); ctx.fill();
    ctx.restore();
    QUICK.forEach((q, i) => {
      const p = E.out3(prog(t, P[1] + i * 0.12, 0.5));
      if (p <= 0) return;
      const y = cBox.y + 34 * U + i * ((cBox.h - 60 * U) / QUICK.length);
      textBlock(ctx, q[0], { x: cBox.x + 30 * U, y, w: cBox.w * 0.52, h: 40 * U }, { role: 'label', color: COL.acc, t: 0, alpha: p, valign: 'middle', size: 25 * U });
      textBlock(ctx, q[1], { x: cBox.x + cBox.w * 0.54, y, w: cBox.w * 0.44 - 30 * U, h: 40 * U }, { role: 'caption', color: COL.termInk, t: 0, alpha: p, valign: 'middle', size: 23 * U });
    });

    // 落版：文档站 + 仓库 + 安装
    const pf = E.out3(prog(t, P[2], 0.6));
    const fy = urlY;
    textBlock(ctx, 'variableway.github.io/spark-cli', { x: R.x, y: fy, w: R.w, h: 44 * U }, { role: 'label', color: COL.acc, t: 0, alpha: pf, valign: 'middle', size: 30 * U });
    textBlock(ctx, 'github.com/variableway/spark-cli', { x: R.x, y: fy + 44 * U, w: R.w, h: 40 * U }, { role: 'caption', color: COL.ink2, t: 0, alpha: pf, valign: 'middle', size: 23 * U });
    const mbY = STACK ? nm.y + nm.h + 96 * U : B.y + B.h - 48 * U;
    textBlock(ctx, 'make build  →  ~/.local/bin/spark', { x: L.x, y: mbY, w: L.w, h: 44 * U }, { role: 'caption', color: COL.ink2, t: 0, alpha: pf, valign: 'middle', size: 23 * U });
  };

  // ---------------------------------------------------------------- 音效：打字、落定、落版
  const S1 = SCN('S01'), S2 = SCN('S02'), S3 = SCN('S03'), S4 = SCN('S04'), S5 = SCN('S05'), S6 = SCN('S06');
  for (let i = 0; i < 14; i++) EV(S1.t0 + 0.06 + i * 0.058, 'key', { n: i });     // 命令一个个敲出来
  for (let i = 0; i < 22; i++) EV(S1.t0 + 1.0 + i * 0.175, 'tick_soft', { pitch: i % 4 });   // 输出逐行打印
  [0, 1, 2].forEach(i => EV(S2.t0 + 0.1 + i * 2.6, 'ping', { n: i }));        // 四条能力标注出现
  EV(S2.t0 + 0.1, 'pluck', { n: 0 });
  EV(S3.t0 + 0.05, 'whoosh_in', { dur: 0.5 });
  EV(S3.t0 + 0.9, 'num_hit', { big: true });
  EV(S4.t0 + 0.05, 'swish', { dur: 0.6 });
  EV(S4.t0 + 5.2, 'swish', { dur: 0.6 });
  EV(S5.t0 + 0.05, 'chord_lift', {});
  for (let i = 0; i < 8; i++) EV(S5.t0 + 0.3 + i * 0.07, 'tick', { n: i });
  EV(S5.t0 + 2.4, 'chime_up', {});
  EV(S6.t0 + 0.05, 'logo_hit', {});
  EV(S6.t0 + 3.4, 'bell', {});
})();
