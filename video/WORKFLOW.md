# spark-cli 介绍片 · 工作流

52 秒的中文介绍片，三种画幅（16:9 / 9:16 / 1:1）从同一份工程导出。
画面里的每条命令、每个版本号、每个 URL 都是真的——这一点由事实核对器
在渲染前逐条核对，不是靠人记。

## 工具链是两个 Skill，工程只放项目数据

这支片用两个 Skill：

| Skill | 是什么 | 副本在 |
|---|---|---|
| `cli-intro-video` | 工作流层：录素材、事实核对、裁剪自检、流水线、脚手架 | `video/skills/cli-intro-video/` |
| `lucid` | 引擎层：代码视频框架（镜头代码 → 逐帧渲染 → MP4 → 体检 → 交付核对） | `video/skills/lucid/` |

两个 Skill 都**整份复制进本目录**，工程因此是自洽的：不依赖某个人的
`~/.minimax` 目录，也不需要联网去插件缓存里找模板。原件同时留在用户目录里
（`~/.minimax/agents/mavis/skills/cli-intro-video/` 和插件缓存里的 lucid），
那边是「活的」版本——改脚本先改原件，再同步回本目录。

```
video/skills/cli-intro-video/
├── SKILL.md              什么时候用这套流程、怎么用
├── scripts/              record_terminal / facts / check_crop / pipeline / scaffold
└── references/           工作流详解、profile 字段说明、踩坑记录

video/skills/lucid/
├── SKILL.md              引擎入口（25 行）
├── PROVENANCE.md         来源与授权说明，务必保留
├── references/           11 篇：引擎接口、素材、配音、工艺、片型指南、踩坑
├── capabilities/         宿主能力说明（配音、转写等）与退路
└── template/             框架模板原件（21 个工具脚本 + web 引擎 + 示例工程）
```

**lucid 是什么**：一个「用代码写视频」的引擎。画面不是拖模板拼的，而是你写一段
JavaScript 描述「第 t 毫秒这一帧该长什么样」，引擎用 Chrome 逐帧渲染、按镜头切段
并行渲染、再用 ffmpeg 合成 MP4；另有自动体检（版面、字幕、响度、空帧、运动量）
和交付核对。片型分explainer / promo / review 等，各自的参考文档在 `references/`。

它的总体思路可以记成五句话：

1. **画面只由时间算出**——镜头函数只依赖 `t`，不存状态、不用 `Math.random()`。
   正因如此，引擎才能逐帧渲染、分段并行、只重渲改过的那一个镜头。
2. **代码就是分镜**——引擎给的是一套排版与运动的词汇表（分区、文字块、弹簧、拍点、
   坐标、标注、数据映射），写镜头就是用这些词把分镜做出来。
3. **时间轴决定一切**——`beats` / `manual` / `voice` 三种模式；讲解片用配音驱动，
   画面事件挂在短句上，声音和画面天生对齐。
4. **迭代用草稿档，最后只出一次正式档**——草稿档半尺寸、快，用来反复看结构节奏；
   正式档开运动模糊，并跟草稿逐帧比对查重影。
5. **验收靠机器，不靠人眼**——渲染前合同/页面/版面三道预检，渲染后体检分硬伤与
   可选提示两级，交付时按成片事实逐条填核对表。

详细接口看 `video/skills/lucid/references/engine.md`，完整版说明在架构页的
「一、lucid 的总体思路」。

**分工**：`lucid` 负责「画面好不好看」，`cli-intro-video` 负责「画面里的是不是真的」——
终端素材是命令真跑一遍录的，画面上每个数字和 URL 都有一条可执行的检查。

## 目录

```
video/
├── profile/          这支片讲谁：工具元数据、素材录制参数、画面上的每个事实
│   ├── spark-cli.json    二进制怎么构建、命令、URL、命令族、每个素材的裁剪范围
│   └── facts.json        画面上出现的事实 → 它的来源和校验方式
├── skills/           用到的两个 Skill 的完整副本（改脚本先改原件再同步回来）
│   ├── cli-intro-video/  工作流层：录素材 / 事实核对 / 裁剪自检 / 流水线
│   └── lucid/            引擎层：框架模板原件 + 11 篇参考 + 宿主能力说明
├── docs/             架构图与模块图（自包含单页，点文件名可看源码）
├── project/          lucid 框架的工作副本（保持原样，框架升级时可整体覆盖）
│   ├── project.json      片型、画幅、主题、配音
│   ├── script/vo.json    配音稿 + 逐句英译
│   ├── web/shots_spark.js 六个镜头的代码
│   └── tools/            lucid 自带的渲染、体检、交付脚本
├── assets/           素材原料（构建产物等，不进版本库）
└── out/              成片与交付核对（不进版本库）
```

`skills/lucid/template/` 是框架原件，`project/` 是它的工作副本。
两边同名文件里 44 个逐字节相同，只有 3 个不同（`project.json`、`script/vo.json`、
`web/index.html`——最后一个是 `timeline.py` 自动补的 script 标签）；
工作副本另有 177 个独有文件，其中只有 `web/shots_spark.js` 是手写的，其余都是
录制、时间线、配音这些工具的产物。

所以升级框架时**要保住的是 3 个手写文件**：`project.json`、`script/vo.json`、
`web/shots_spark.js`。从 `template/` 重新铺一遍 `project/`，把这 3 个搬回去，
再跑一次 `sync` 让 `timeline.py` 重新生成 `index.html`、`web/project.js`、
`web/timeline.js` 和 `timeline.json` 即可。也可以直接 diff 看看上游改了什么：

```bash
diff -rq skills/lucid/template project
```

**架构图**：整个工程的 lucid 总体思路、分层结构、终端素材的来源、模块与文件的对应关系，
见 [`docs/architecture.html`](docs/architecture.html)——一个自包含的单页，分六节：
lucid 的总体思路、分层架构、终端素材从哪来、原件与工作副本、模块清单、参考资料。

点任意文件名（模块清单里的、分层图里的小标签、或者参考资料里的文档），
右侧会滑出一个抽屉，显示文件路径、大小、所属模块和源码；
抽屉开着时还能接着点下一个文件换内容，可以拖左边缘调宽（宽度会记住），
按 `Esc` 或点抽屉外任意处关闭。

那一页由 `docs/build_architecture.py` 扫描工程生成，工程改了重跑一次脚本就同步：

```bash
python3 video/docs/build_architecture.py
```

**演进计划**：这套流程要变成一个能长期用的 Skill，还差哪些东西——素材层怎么生成的、
改文案为什么难、引擎层有没有硬编码、下一步先做哪一步——见
[`docs/cli-video-skill-plan.md`](docs/cli-video-skill-plan.md)。

## 一条命令跑完

```bash
cd video
project/.venv/bin/python skills/cli-intro-video/scripts/pipeline.py \
  --profile profile --project project --final --format all
```

它按顺序做：

| 步骤 | 做什么 | 不通过会怎样 |
|---|---|---|
| facts | 跑 `profile/facts.json` 里每条事实的来源，逐条比对 | 退出码 1，**不渲染** |
| crop | 按真实输出行宽核对每种画幅的裁剪范围；核对 profile 与镜头代码的 CARD 表一致；核对镜头代码的几何常量和素材真实网格一致 | 退出码 1，**不渲染** |
| record | 按 `profile/spark-cli.json` 的 capture 参数重录终端素材（默认跳过，加 `--record` 才跑） | 退出码 1 |
| sync | 重跑 `tools/timeline.py`，刷新 `web/project.js` 里的序列帧清单 | 退出码 1 |
| render | `project/tools/render.py`，渲完自动体检 | 体检有硬伤就按报告改 |
| deliver | `project/tools/deliver.py`，打印成片事实并更新 `out/交付核对.md` | — |

单步重跑：`--only facts,crop`、`--only render` 等。
草稿档（默认，半尺寸快速）用来迭代，正式档加 `--final`。

## 改了画面上的事实，要同时改 facts.json

画面上写了「v0.4.0」，观众会当真。改了版本号、改了命令列表、改了 URL，
**必须**同步改 `profile/facts.json`，否则事实核对会拦下来。

写法：

```json
{
  "id": "version",
  "on_screen": "v0.4.0 / commit 745cd48",
  "where": "S03 版本卡",
  "check": {
    "type": "command",
    "command": ["version"],
    "expect_all": ["spark v0.4.0", "commit:     745cd48"]
  }
}
```

检查类型：

- `command`：跑这条命令（默认用 profile 里的二进制），输出必须包含 `expect_all` 的每一串。
  不是 spark 的子命令时加 `"binary": false`；要在仓库根跑时加 `"cwd": "repo"`。
- `file`：读仓库根的某个文件，内容必须包含 `expect` 的每一串。
- `quick_commands`：逐条跑 `profile.quick_commands` 里每条的 `--help`，确认子命令存在。
- `manual`：机器核不了，必须人工确认，`reason` 里写清为什么核不了。
  机器核不了又确实该上画面的事实，就人工确认后留在清单里，别假装它被核过了。

## 改裁剪范围

裁剪范围在两个地方：`profile/spark-cli.json` 的 `assets.<名>.crop`，和
`project/web/shots_spark.js` 的 `CARD` 表。**两边要一致**，
裁剪自检会对照；只改一边会被拦下来。

裁剪范围的列数不能小于这一段里最长的一行——超出的部分会在画面上被卡片边缘切掉，
而体检量不到图片里的字。所以先跑裁剪自检看「最宽一行 N 列」，列数要 ≥ N。

## 重录素材

```bash
project/.venv/bin/python skills/cli-intro-video/scripts/record_terminal.py \
  --name help --cmd "/tmp/spark-new --help" --prompt '$ spark --help' \
  --cols 92 --rows 23 --fps 15 --head 22 --out-width 1250 --seq-sec 12 --still --cps 16 \
  --project project
```

参数在 `profile/spark-cli.json` 的 `assets.<名>.capture` 里，`pipeline.py --record`
会照着跑一遍。

**录完素材后一定要做一件事**：把 `project/web/img/<素材>/meta.json` 里 `cell` 字段的
四个数（`cw` / `ch` / `pad_x` / `top`）抄进 `shots_spark.js` 顶部的几何常量。
镜头代码的 `rowAt()` 靠它们把「素材第 k 行」换算成画面坐标做标注。

这四个数**不是**「画幅宽 ÷ 列数」之类的名义值：素材文本区两侧留了内边距
（1250px 宽里文字只占 1212.6px），用名义值会让裁剪框超出素材边界，
浏览器只能横向压掉一截——字被拉宽，标注线也整体偏 3%。裁剪自检会拿这两个值
逐个比对，对不上就拦下来，所以别手算，抄 `meta.json`。

**重录完还要同步一次**：`web/project.js` 里的序列帧清单是扫描 `web/img/*/` 得来的快照，
帧数变了它就过期，页面会按旧帧号去加载已经不存在的图片，渲染一启动就白屏。
跑 `project/.venv/bin/python project/tools/timeline.py` 刷新它（流水线的 `sync` 步骤也做这件事）。

## 交付

成片在 `project/out/`，`out/交付核对.md` 是交付核对表。
`deliver.py` 会把成片事实（时长、画幅、响度、字幕语言、画面文字语言）填进去，
硬约束逐条填「做到了，第几秒」。事实核对表也在同一份文件里。

成片另外拷到仓库的 `docs/assets/video/`，供文档站嵌入；
改动成片后要同步更新那一份，并重新生成 poster 图。
