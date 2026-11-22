---
name: cli-intro-video
description: |
  给命令行工具做介绍片：真实执行命令录成无损帧序列做终端素材，渲染前逐条核对画面上每个事实，
  按 profile 驱动多画幅（16:9 / 9:16 / 1:1）出片。Use this skill when the user asks to make an
  intro / promo / demo video for a CLI or developer tool, wants a terminal recording turned into
  a video, needs the same tool video in several aspect ratios, or asks to add a video workflow
  for a new tool. Triggers on 「给这个 CLI 做介绍片」「录个终端演示视频」「出一版竖版」「工具宣传片」
  / CLI intro video / terminal demo / multi-format tool video.
  Do not use it for editing or polishing an already-finished video, for generic screen recording,
  or for slides — that is the `lucid` skill's own territory, and this skill is the layer above it.
descriptions:
  zh-Hans: "给命令行工具做介绍片：真实录屏素材 + 事实核对 + 多画幅渲染。"
displayNames:
  zh-Hans: "CLI 介绍片"
---

# CLI 介绍片

在 lucid 代码视频框架之上，做「真实录屏 + 内容可核对」的命令行工具介绍片。

这个 skill 是 lucid 的**上游层**：lucid 负责把画面画出来（镜头代码、渲染、体检、交付核对），
这个 skill 负责让画面里的东西**是真的**——终端素材是命令真跑一遍录的，
画面上的每个数字和 URL 都有一条可执行的检查，渲染前对不上就停。

## Inputs to collect

开工前先确认这几件事，缺了就问，不要猜：

1. **被介绍的工具**：叫什么、二进制在哪个路径、怎么构建（`make build` / `go install` / `npm i -g`）。
   构建不出来后面全做不了——先让它能跑。
2. **画面上要讲哪几件事**：三到六条。挑「用户第一次用会关心」的，不是「功能清单」。
3. **画幅**：默认 16:9 + 9x16 + 1:1 三份同源。只出一份也行。
4. **配音与字幕语言**：默认跟随用户语言。
5. **成片放哪**：只出片，还是嵌进文档站（后者要同步拷成片和 poster 图）。

工具链：本 skill 的 `scripts/`（Python，标准库 + 工程已有的 Pillow）+
lucid skill 的框架模板。lucid 的模板要先用 `skill({ name: "lucid" })` 读出 Location，
它的目录名带哈希，脚本会自己 glob 找，也可以用 `--template` 或 `LUCID_TEMPLATE` 指定。

## Procedure

### 1. 起工程

新工具用脚手架，已有工程直接用：

```bash
python3 scripts/scaffold.py --dest ../mytool-video --name mytool \
  --title "My Tool" --binary /usr/local/bin/mytool --build "make build"
```

脚手架产出 `profile/`（工具元数据 + 事实清单）、`project/`（lucid 模板副本）和一个镜头骨架。
**不要**去改 lucid 模板的源码，只改副本——框架升级时整体替换即可，自己的代码只有一个镜头文件。

搭好 Python 环境（lucid 的依赖）：

```bash
cd project && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

依赖装到工程 `.venv`，不装进系统 Python，也不复制框架的插件目录。

### 2. 写 profile

`profile/<name>.json` 声明这支片讲谁：二进制怎么构建、链接、命令族、要录哪几段素材、
每种画幅裁多少行多少列。字段说明见 `references/profile-schema.md`。

关键约束：**profile 是声明的真相，镜头代码里的 CARD 表是实现的真相，两边必须一致**。
不一致时 `check_crop.py` 会把两边对照着报出来。

### 3. 录素材

```bash
.venv/bin/python <skill>/scripts/pipeline.py --profile ../profile --project . --record --only record
```

命令是真的执行一遍，输出原样采集；节奏（逐字输入、逐行打印、停顿）是脚本合成的，
因为真实命令几十毫秒就跑完了，直接录会像视频卡住。

只用作静态卡片的素材（`capture.seq: false`）不产出序列帧，只留静帧——省几十 MB。

重录后要同步一次 `web/project.js`：里面的序列帧清单是扫描 `web/img/*/` 得来的快照，
帧数变了它就过期，渲染一启动就会白屏。流水线的 `sync` 步骤做这件事
（`tools/timeline.py`），不用手敲。

### 4. 把几何常量抄进镜头代码

录完素材后，读 `project/web/img/<素材>/meta.json` 的 `cell` 字段，把
`cw` / `ch` / `pad_x` / `top` 四个数抄进镜头代码顶部的 `CH` / `TOP` / `COLW` / `PADX`。

这四个数**不能自己估**：素材文本区两侧留了内边距，「画幅宽 ÷ 列数」是名义值，
用它会让裁剪框超出素材边界，浏览器只能横向压掉一截——字被拉宽，标注线整体偏 3%。
抄 `meta.json`，别手算。

### 5. 写镜头代码

`project/web/shots_<name>.js`。lucid 的镜头约定（`SHOT.<id>` 的签名、`textBlock` / `img` 的参数、
`seqFrame` / `safeBox` 怎么用）见 lucid skill 自己的 references 目录。两条最要紧的：
画面只由 `t` 算出，`EV()` 写在文件顶层。

终端素材按「行区间 + 列区间」裁剪，标注层用 `rowAt()` 把「素材第 k 行」换算成画面坐标。
一个镜头里换裁剪范围会让卡片在切点处变形——连续播放的两帧用同一套裁剪。

### 6. 写事实清单

`profile/facts.json`：画面上出现的每个事实，写清「画面上写什么」和「怎么核」。
检查类型有 `command` / `file` / `quick_commands` / `manual`，写法见 `references/profile-schema.md`。

核不了的（随环境变、会过期的）就用 `manual` 并写清理由，不要假装它被核过了。
比如「本机装了几个技能」这种写进片子就会变成一条随时会过期的事实——干脆不写。

### 7. 把关

```bash
.venv/bin/python <skill>/scripts/pipeline.py --profile ../profile --project . --only facts,crop
```

两条都过才允许渲染。任一条不过就停在那一步，不要带着问题渲染。

### 8. 渲染与交付

```bash
.venv/bin/python <skill>/scripts/pipeline.py --profile ../profile --project . --final --format all
```

`render.py` 渲完自动体检（硬约束、字幕、画面文字语言、响度），`deliver.py` 出交付核对表。
体检有硬伤就按报告改，改完复测——不要改报告了事。

配音走 `tools/tts.py`，`voice.provider` 必须是 `mcode`。先 probe 再合成，测得时长再排时间线。

### 9. 嵌回文档站

成片拷到文档站引用的目录，同步更新 poster 图。多画幅用一个播放器切换三种源，
`<video>` 的 src 按页面深度手写——docmd 会改写 markdown 里的链接，但不改 `<video>` 的 src。

## Output contract

- 工程目录：`profile/<name>.json` + `profile/facts.json` + `project/`（lucid 副本 + 镜头文件）
- 素材：`project/web/img/<素材>/`（序列帧 + `meta.json`）与 `project/web/img/<素材>-still.png`
- 成片：`project/out/<output>_<画幅>.mp4`
- 核对表：`project/out/交付核对.md`（成片事实 + 硬约束逐条落实 + 事实核对结果）
- 给用户的回复里要说清：三份画幅各多长多大、体检结果（硬伤几条）、事实核对过了几条

## Failure handling

- **事实和来源对不上** → 停。改画面或改事实来源，别改检查脚本去迁就画面。
  检查脚本是对外的承诺，绕过它等于让片子说假话。
- **某段裁剪会截字** → 加宽裁剪列数，或换一段更短的输出。体检量不到图片里的字，只有这个检查管。
- **profile 与 CARD 表对不上** → 两边都改成一致的。改一边会被对照报出来。
- **几何常量对不上素材** → 抄 `meta.json` 的新值。重录素材后必须重抄。
- **渲染一启动就白屏，报「图片解码失败」** → `web/project.js` 的序列帧清单过期了，
  跑 `tools/timeline.py` 重扫 `web/img/*/`（流水线的 `sync` 步骤也做这件事）。
- **渲染体检有硬伤** → 按报告改画面或改配音稿，复测。不要改报告。
- **配音合成不可用** → 说明情况，允许用户改用自己的录音或接受无配音版本，不要偷偷换服务商。
- **找不到 lucid 模板** → 用 `skill({ name: "lucid" })` 看 Location，再用 `--template` 指定。

## Examples

**Input**: 「给 spark-cli 做一版介绍片，要有横版、竖版和方版。」

**Good path**:
1. `skill({ name: "lucid" })` 读出模板位置；`scripts/scaffold.py` 起工程。
2. profile 写清二进制（`/tmp/spark-new`，`make build` 产出）、命令族、要录的 4 段素材和三画幅裁剪范围。
3. 录素材 → 抄 `meta.json` 的几何 → 写 6 个镜头的代码。
4. facts.json 写 10 条事实（版本号、四条能力、十个命令族、官网、仓库、安装方式…），
   其中「本机装了几个技能」标 `manual` 并说明为什么不写进片子。
5. `facts` + `crop` 全过 → 渲染三份 → 体检 0 硬伤 → 交付核对表 → 拷进文档站。

参考实例：`qdriven/innate-apps/spark-cli` 的 `video/` 目录（profile + 镜头代码 + 工作流说明）。

## Windows (win32) platform notes

这套流程默认在 macOS / Linux 上跑（终端素材要等宽字体和 `make build`）：

- 解释器用 `project\.venv\Scripts\python.exe`（不是 `bin/python`）。
- 字体：录制器按候选列表找等宽字体，Windows 上是 `C:\Windows\Fonts\consola.ttf`，
  也可以 `--font` 显式指定。**换字体等于换网格**——录完必须重抄 `meta.json` 的几何。
- 路径分隔符由 Python 的 `pathlib` 处理，脚本参数里用正斜杠即可。
- `make build` 要在 PowerShell 里配好环境变量（`$env:GOPROXY=...`）。
- 完整跨平台替代方案见 `references/workflow.md` 末节。
