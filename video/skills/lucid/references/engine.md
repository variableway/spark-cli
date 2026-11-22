# 引擎接口：合同、函数、配置

模板 `template/` 是一套可选的工具库。用它的函数写镜头时，看这份接口卡就够，不必读 `core.js` 源码；卡上没有的参数细节，查 `web/core.js` 开头的目录。也可以在镜头里用自己的方式画，只要遵守第一节的合同，最后经 `render.py` 出片。

## 一、合同：画面只由时间算出

这几条是逐帧渲染、分段并行、只重渲一个镜头能成立的前提，不用模板函数时也一样。`render.py` 的预检会拦下第 1、3、4、8 条的违规写法并给出文件和行号；确有理由时在行尾写 `// lint-ok: 原因` 豁免这一行。

1. 镜头函数只依赖 `t`。不用计时器，不在帧之间保存状态，不用 `Math.random()`，随机数用 `rng(种子)`。
2. 一个值要多次变化时，用 `springTo(t, [[t0, 值], [t1, 值], …])` 叠加每次变化的弹簧。循环片用 `springLoop(t, keys, period)`，首尾的位置和速度才对得上。
3. 镜头里设置变换只用 `screen(ctx)` 和 `cam(ctx, …)`。`setTransform(1,0,0,1,0,0)` 会丢掉全局矩阵，转场位移和震动就失效了，镜头矩阵也登记不到，抖动检查无从量起。
4. 音效在动作发生的那一刻登记：`EV(t, '名字', {…})`，写在镜头文件的顶层，不写在绘制函数里（导出音效时不调用绘制函数）。时刻用和画面相同的表达式算，例如 `b(8)`、`ph('S03', 1) + 0.4`。t 是动作那一刻，合成器按每个音效的对齐方式自动提前（`python3 audio/synth.py --list-fx` 列出）。
5. 网页只加载 `web/shots_*.js`。共用函数也放进 `shots_*.js`（例如 `shots_00_common.js`）。增量渲染按镜头所在的文件判断要不要重渲，改了 `shots_00_*`、引擎或 `project.json` 会整片重渲，所以每个镜头最好单独一个文件。新字体写进 `theme.font_files`（格式见 [pitfalls.md](pitfalls.md)）。
6. 背景由引擎每帧先画（`theme.colors.bg`），镜头里不铺底。相邻镜头重叠转场时，后画的镜头一铺底，前一个镜头就被整个盖掉。
7. 拍子是动作的落点。`enter(t, tb)` 让入场提前几帧开始，`land(t, tb, dur)` 让动作恰好在 tb 落位。从拍点才开始入场，那一帧就是空画面。
8. 衰减用 `decay(t, t0, tau)`，不直接写 `Math.exp(-(t - t0) / tau)`：t 早于 t0 时（pre 重叠段、提前起手）它会变成几十上百倍，把元素放大成怪形。

## 二、接口卡

镜头写法：`SHOT.S03 = function (ctx, t, S) { … }`，t 是全局秒，`S = {t0, t1, dur, phrases}`。

**命令**（都在工程根目录运行）

| 命令 | 做什么 |
|---|---|
| `python3 tools/timeline.py [--estimate]` | 把 `project.json` 同步到网页，打印每个镜头的起止；讲解片还没配音时 `--estimate` 按音节估时 |
| `python3 tools/tts.py voices [--lang zh\|en]` / `tts.py audition "<一句话>" <音色1> <音色2>` | 列出可用音色 / 用同一句话试读几个音色，存到 `audio/audition/`，打印时长和转写 |
| `python3 tools/tts.py full v1` | 整段合成配音，合成后自动转写，打印和稿子对不上的名字、数字、英文词；`tts.py asr current` 单独重跑转写 |
| `python3 tools/tts.py once args.json out.mp3 [--asr]` | 试读一个短句，比较几种写法 |
| `python3 tools/stills.py S03` | 静帧：这个镜头 0.3、0.6、0.9 处三帧。指定时刻写 `stills.py [名字] S03@0.3,S03+1.2,b12,7.5`（镜头 30% 处、镜头内 1.2 秒、第 12 拍、绝对秒），不写名字时自动起名；`--all 0.3,0.7` 每镜两帧，`--every beat` 每拍一帧，`--cuts` 转场逐帧条，`--between b8-b12` 变形中途 |
| `python3 tools/stills.py --props` | 物件表：每个 `PROP` 放大画几个时刻 → `frames/_view/props.jpg` |
| `python3 tools/dump_events.py && python3 audio/synth.py` | 导出音效事件，合成配乐、音效、人声并校准响度。`render.py` 渲染前会在需要时自动跑 |
| `python3 tools/render.py` | 草稿档 → `out/<名字>_draft.mp4`。预检、增量渲染、自动体检，打印摘要和成片的时长、画幅、有无声音 |
| `python3 tools/render.py --final [起 止]` | 正式档 → `out/<名字>.mp4`，渲完和草稿档比对重影；`--format all` 出全部画幅 |
| `python3 tools/checkup.py` | 不重渲，单独重跑体检 |
| `python3 tools/deliver.py` | 打印成片事实，写出 `out/交付核对.md`；`--final` 结束时自动运行 |
| `python3 tools/assets.py <子命令>` | 截图、logo、品牌色、产品图、视频帧，见 [assets.md](assets.md) |
| `python3 tools/srt.py` | 字幕文件，和字幕层用同一份短句，有英文时出双语 |

**版面与文字**（矩形都是 `{x, y, w, h}`，在 `screen(ctx)` 的版面坐标里）

| 签名 | 做什么 | 例子 |
|---|---|---|
| `W` `H` `U` `PORTRAIT` `SQUARE` | 画幅宽高；`U` = 短边 / 1080 | `40 * U` |
| `safeBox()` | 安全区，四边各留短边 5%；字幕层开着时底边让出字幕带 | `const R = safeBox()` |
| `split(box, dir, parts, gap = 0)` | `'row'` 左到右、`'col'` 上到下按权重切 | `const [a, b] = split(R, 'row', [3, 2], 40 * U)` |
| `grid(box, cols, rows, gap = 0)` | 行优先切成 cols × rows 格 | `grid(b, 2, 3, 24 * U)[i]` |
| `inset(box, m)` | 四边各收 m，或 `[上, 右, 下, 左]` | `inset(a, 32 * U)` |
| `fit(box, w, h, o)` | 自然尺寸 w × h 的物体等比放进 box，返回 `{x, y, w, h, s}`；`o.fill` 0–1（默认 1）、`o.align` `'center'`（默认）`'top'` `'bottom'` `'left'` `'right'`，可组合 `'top left'` | `const f = fit(a, 600, 420, {align: 'bottom'})` |
| `PROP.名字 = function (ctx, t, o) {…}`、`PROP.名字.size = [w, h]`；`prop(ctx, name, box, o)` | 登记主角物件，按自然尺寸画、原点在左上角，`size` 必填 / 用 `fit` 放进 box，返回 fit 的结果；`o.fill` `o.align` 同 fit，`o.t` 传给物件的时间（默认当前 t），`o` 原样传给物件 | `prop(ctx, 'tree', stage, {align: 'bottom', up})` |
| `textBlock(ctx, text, box, o)` | 断行、定字号、画字、入场，返回 `{size, lines, fits, …}`。`o.role` 定字重、字号上限（× U）和默认色：`title` 标题（700，132）、`body` 正文，默认（500，54）、`label` 标签（600，40，ink2）、`number` 大数字（700，220）、`caption` 注释（400，34，ink2）。排版 `o.lines` `o.min` `o.max` `o.size` `o.align` left/center/right、`o.valign` top/middle/bottom `o.lh`（默认 1.25）`o.ls` `o.color`；入场 `o.t` `o.at` `o.style` rise/slam/fade/type/none（type 的速度 `o.cps`，默认 18 字/秒）、`o.out` 退场进度，`o.anchor`；`o.sizeText` 按另一段字定字号（并列的几块字号一致、滚动的数字字号不跳） | `textBlock(ctx, '水从根部进来', b, {role: 'title', t, at: ph('S02', 0)})` |
| `textBlockMeasure(text, box, o)` | 同样排版，只量不画 | `textBlockMeasure(s, b, {role: 'body'}).size` |
| `txt(ctx, s, x, y, o)` | 单行字；`o.font` `o.color` `o.align` `o.base` `o.alpha` `o.deco` | `txt(ctx, '42', x, y, {font: F.m(48 * U)})` |
| `riseLine(ctx, s, x, y, lt, o)` / `slamLine(…)` | 逐字升起 / 砸字；lt 是出字后的秒数 | `slamLine(ctx, 'NOW', x, y, enter(t, b(16)))` |
| `typeOn(ctx, s, x, y, t, t0, o)` / `rollWords(ctx, items, t, x, y, o)` | 打字机，返回已打字数 / 同一位置换词 | `typeOn(ctx, cmd, x, y, t, ph('S04', 0))` |
| `F.d(px)` `F.b(px)` `F.m(px)` `F.s(px)`；`measure(s, font)` | 标题、正文、等宽、衬线字体；量宽 | `measure('168', F.m(40 * U))` |

**时间与动作**

| 签名 | 做什么 | 例子 |
|---|---|---|
| `b(n)`；`ph(id, k)`、`phE(id, k)` | 第 n 拍的时刻；镜头 id 第 k 个短句（从 0 起，按标点切分）的起、止 | `ph('S03', 1)` |
| `act(t, at, o)` | 画面事件：从 at 起按 `o.ease`（默认 `E.out3`）走完 `o.dur`，返回 0–1；`o.name` 写事件名，`o.lead` 提前起手。讲解片 `dur` 默认取短句时长的 40%（0.4–1.2 秒），宣传片默认 1 拍 | `const k = act(t, ph('S03', 1), {name: '水柱上升'})` |
| `springTo(t, keys, f, z)` / `spring(t, f, z)` / `springLoop(t, keys, period)` | 多段弹簧 / 单次弹簧 / 循环片弹簧 | `springTo(t, [[S.t0, 0], [ph('S02', 1), 1]])` |
| `enter(t, tb, lead)` / `land(t, tb, dur, ease)` | 入场提前起手 / 恰好在 tb 落位，返回 0–1 | `lerp(x0, x1, land(t, b(8), 0.3))` |
| `prog(t, a, d)`、`decay(t, t0, tau)`、`lerp`、`clamp`、`E.out3` `E.inOut5` `E.outBack` … | 进度、衰减、插值、缓动 | `E.out3(prog(t, a, 0.5))` |
| `stagger(t, n, gap, o)` | 一组元素先后落位；`o.order` index/reverse/center/edges/point/random，`o.dur` 时返回进度 | `stagger(t - S.t0, 6, 0.06, {dur: 0.4})` |
| `follow(t, leader, o)` | 带延迟和弹性地跟随一个运动的主体；`o.delay` `o.f` `o.z` | `follow(t, P, {delay: 0.08})` |
| `rng(seed)` | 可复现的随机数 | `const r = rng(7); r()` |

**镜头、标注、图形与登记**

| 签名 | 做什么 | 例子 |
|---|---|---|
| `screen(ctx)` / `cam(ctx, cx, cy, z, rot)` | 版面坐标 / 镜头看向 (cx, cy)、缩放 z | `cam(ctx, ...camKeys(KEYS, t))` |
| `camKeys(keys, t, ease)` / `drift(t, S, o)` | 关键帧镜头 / 整段缓推加慢弧线，自动不出安全区 | `cam(ctx, ...drift(t, S, {push: 0.04}))` |
| `idle(t, i, o)` / `handheld(t, amp, seed)` | 次要元素的慢浮动 / 手持感 | `const m = idle(t, i)` |
| `chartScale(o)` | 数据到像素的唯一映射：`o = {data, box, min, max}`，box 直接用分区得到的矩形，返回 `x(i)` `y(v)` `bar(i, w)` | `const C = chartScale({data, box: stage, min: 0})` |
| `anchor(ctx, name, x, y, w, h)` / `callout(ctx, target, from, o)` / `pin(ctx, C, value, o)` | 画目标时登记它 / 引线从 from（`screen` 下的版面坐标，或另一个锚点名）画到目标边缘，同一帧里先 anchor 后 callout / 按数值标记，`o.at` 立在数据点上，不给 at 画参考线 | `callout(ctx, 'cell', [lx, ly], {p: k, elbow: 'h'})`；`pin(ctx, C, 9, {at: 3, label: '最高 9'})` |
| `drawPath(ctx, pts, u, o)` | 按进度 u 画折线，返回笔尖位置；`o.color`（默认 ink）`o.lw` 线宽 px（默认 3，不随画幅缩放，写 `3 * U`）`o.alpha` `o.dash` `o.arrow` 箭头大小 px | `drawPath(ctx, pts, k, {lw: 3 * U})` |
| `rrect(ctx, x, y, w, h, r)`、`glow(ctx, x, y, r, color, a)` | 圆角矩形只建路径，之后自己 `ctx.fill()` 或 `ctx.stroke()` / 以 (x, y) 为中心、半径 r 的加亮光晕，a 是中心透明度（默认 0.25） | `rrect(ctx, x, y, w, h, 24 * U); ctx.fill()` |
| `img(ctx, name, x, y, w, h, o)`、`seqFrame`、`frameAt(秒, 宽)` | 图片（`o.fit` cover/contain/fill、`o.r`、`o.src`）/ 序列帧 / 本片任意时刻的一帧 | `img(ctx, 'shot', x, y, w, h, {fit: 'cover', r: 24})` |
| `appWindow(src, o)`、`GL3D.card(ctx, o)`、`cursor(ctx, x, y, o)`、`shatter(ctx, src, x, y, w, h, p, o)` | 应用窗口外框 / 透视卡片 / 光标 / 碎片拼合 | `GL3D.card(ctx, {img: 'shot', x, y, w, h, ry: 14})` |
| `COL.bg` `COL.ink` `COL.acc` …、`hexA(c, a)`、`mixHex(a, b, u)`、`parseColor(c)` | `theme.colors` 里的颜色 / 加透明度 / 混色 / 拆成 `[r, g, b, a]`。都接受任何 CSS 颜色（`#rgb`、`#rrggbb`、`rgb()`、`rgba()`），`mixHex` 返回 `#rrggbb`，可以嵌套 | `hexA(mixHex(COL.acc, COL.bg, 0.3), 0.8)` |
| `EV(t, name, o)`、`SHAKES.push([t0, 幅度, 衰减])`、`FLASH`、`FAST.push([t0, t1, 16])` | 音效、震屏、闪光、给某段指定运动模糊的采样下限（可选）；都写在文件顶层 | `EV(ph('S02', 1), 'pop')` |

用模板函数时，一个镜头的典型写法：登记物件、分区、放主体、出字、登记事件。

```js
PROP.tree = function (ctx, t, o) { /* 按 600 × 720 的自然尺寸画，o.up 是水柱进度 */ };
PROP.tree.size = [600, 720];
SHOT.S02 = function (ctx, t, S) {
  screen(ctx);
  const [stage, side] = split(safeBox(), PORTRAIT ? 'col' : 'row', [3, 2], 48 * U);
  const up = act(t, ph('S02', 1), { name: '水柱上升' });
  prop(ctx, 'tree', stage, { align: 'bottom', up });
  textBlock(ctx, '水沿着细管往上走', side, { role: 'title', t, at: ph('S02', 1) });
};
EV(ph('S02', 1), 'pop');
```

`template/examples/` 有两个能直接运行的示例，用法写在各自 `shots_demo.js` 的开头：`promo_beats/`（节拍片，横竖两个画幅）和 `explainer_voice/`（配音驱动的短讲解片：分区排版、物件表、文字块、按短句登记事件、标注和图表）。它们演示机制，配色、版式和节奏换成自己片子的。

## 三、可配置的维度

都写在 `project.json`，改完运行 `timeline.py`。模板里的值只是起点。

| 维度 | 写法 |
|---|---|
| 配色和字体 | `"theme": {"colors": {"bg", "ink", "acc", …}, "fonts": {"display", "body", "mono", "serif"}}`。引擎不带默认配色，`bg`、`ink`、`acc` 缺了 `timeline.py` 会停下（定法见 [craft.md](craft.md)「配色从场景推」）；`ink2`、`dim` 缺省时由 ink 和 bg 混出；字体缺省用系统字体 |
| 画幅 | `"canvas": {"w": 1080, "h": 1920}`；用户要了多个画幅时用 `"formats": {"16x9": {…}, "9x16": {…}}`。版面用分区和 `W`、`H`、`U`、`PORTRAIT` 写，同一套镜头出多个画幅 |
| 片型 | `"genre": "promo" \| "explainer"`：决定体检的字号下限、指标阈值和 `act()` 的默认时长 |
| 帧率 | `"fps"`：宣传片 60，讲解片 30。草稿档最高 30 帧，正式档按这里的值 |
| 时长 | `"target_sec"` 是用户说的时长；`"timeline": {"total": 15.0}` 或 `"tail": 0.5` 补齐整数秒，不改 BPM 凑数 |
| 时间轴 | `"timeline": {"mode": "beats" \| "manual" \| "voice", …}`，`timeline.shots` 里每个镜头可写 `"motion": "稳" \| "可以震"`（体检只在「稳」镜头里量抖动） |
| 转场 | `SHOT.S02 = {pre: 0.3, post: 0.5, draw(ctx, t, S) {…}}`，重叠段的转场写在镜头里；`transitions` 只提供横推、淡化这类通用转场 |
| 循环 | `"loop": true`：`render(total)` 等于 `render(0)`，做完用 `tools/loopcheck.py` 查接缝 |
| 声音 | `"music": {"source": "synth" \| "file" \| "none", "style", "sections", "kicks"}`；配音参数在 `"voice"`（后端、音色、语速、`why` 选这个声音的理由，见 [../capabilities/README.md](../capabilities/README.md)） |
| 字幕 | `"subtitles": {"burn": true, "langs": ["zh", "en"]}`：配音驱动的片子可用，引擎按配音短句在底部字幕带烧录字幕，`safeBox()` 让出这条带；英文写在 `vo.json` 每个镜头的 `"en": [...]`，一个短句一条，缺了 `timeline.py` 会停下。用户要字幕、双语或静音可看时打开；没要求时不开，只出 SRT |
| 素材 | 图片放 `web/img/`，序列帧放 `web/img/<名字>/`；`img()`、`seqFrame()` |
| 运动模糊 | `"motion_blur": {"samples": 2, "shutter": 0.5, "max": 128}`，只在正式档生效：引擎按画面变化在 `samples`（下限）和 `max`（默认 128）之间取采样数，静止帧只画一次；`FAST` 可选，手动给某段指定下限 |
| 后期层 | `"post": {"grain", "vignette", "fadeIn", "fadeOut"}`。宣传片不开 `fadeIn`，第一帧必须有内容 |
| 版式模块 | `"modules": ["editorial"]`：可选，适合调研汇报类讲解片，见 [explainer.md](explainer.md) |
| shader 背景 | `"background": {"preset": […]}`：默认不开，背景本身是设计的一部分时才开，见 [shader-background.md](shader-background.md) |
