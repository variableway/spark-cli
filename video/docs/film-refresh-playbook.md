# 改片手册 · CLI 变了以后怎么把片子跟上

**触发场景**：CLI 改了命令树、某个命令的输出变了、版本号变了、README 改了「最常用命令」的优先级。

这片子的画面里出现的每一条命令、每一个版本号、每一段终端输出，都是**录进去的真东西**。
所以 CLI 一改，片子不会自动跟上——它会变成一个说假话的片子，而且这种假话机器不一定拦得住。

这份手册是 2026-11-22 那次实战改出来的（`4a7db1f` 把 `spark repo` 折进 `spark hub`、
删掉 `spark skill` 与 `git submodule/sync/init`），每一步都是当时真跑过的。

配套的第二篇讲**结构**——每个文件是什么、谁产出谁消费、改完之后按什么路径重跑：
[改片手册（二）· 输入输出结构与手动流程](film-refresh-io.md)。

---

## 0. 先判断：这次要改哪几环

| 变了什么 | 要动的地方 | 代价 |
|---|---|---|
| 命令族增删改名 | profile `command_families` + facts `command_families` + 镜头 `FAMS` + 配音 | 秒级～分钟级 |
| 某个子命令的输出变了 | 重录该素材 + 镜头里的标注行号 | 十分钟级 |
| 版本号 / commit / 构建时间 | 重录 `version` 素材 + facts `version` + 镜头 `L_VER` | 十分钟级 |
| README 的命令优先级变了 | profile `quick_commands` + facts `quick_commands` + 镜头 `QUICK` + README 本身 | 分钟级 |
| 终端素材改名 | profile `assets` 的 key + 镜头 `CARD` 表 + 镜头 `term()` 的引用 + 删旧素材 | 十分钟级 |
| 只是文案措辞 | 镜头里的字面量 + 配音稿 | 秒级（只改镜头）／分钟级（改配音） |

**一句话**：只要动了 `vo.json` 的文案，就是分钟级（要重录配音）；只要动了素材，就是十分钟级。

---

## 1. 顺序：为什么是这个顺序

```
改源码
  └─ make build                ① 二进制必须先新，否则后面全在给旧二进制做_checks
       └─ 改 profile/*.json    ② 声明层：命令清单、素材怎么录、裁多少
            └─ 改 facts.json   ③ 断言层：画面上每句话的来源
                 └─ 改镜头代码  ④ 表现层：字面量、标注行号、卡片
                      └─ 改配音稿 ⑤ 节奏层：短句数和 ph() 索引绑着
                           └─ 重录素材 ⑥ 画面层：真实输出
                                └─ sync → render → deliver
```

**为什么二进制排第一**：事实核对跑的是 `profile.binary.path` 指的那个二进制。
二进制比源码旧一天时，核对器会红——但它拦的是**二进制**，不是画面。
所以每次改完源码第一件事是 `make build`，否则你在追一个假警报。

**为什么配音在镜头之后**：短句数变了，镜头里的 `ph('Sxx', k)` 索引就得跟着调。
先改镜头再改配音。反过来做，很容易让 `ph()` 指向一个还不存在的短句。

---

## 2. 逐环怎么做

### ① 重建二进制

```bash
make build          # 构建 bin/spark，并装到 ~/.local/bin/spark
```

`profile/spark-cli.json` 的 `binary.path` 指的就是它。**指向仓库里的 `bin/spark` 比指向 `/tmp` 好**——
`/tmp` 会被系统清掉，仓库里的产物 `make build` 一句话就回来了。

产物里的版本号/commit 是**构建时**写进去的（Makefile 的 ldflags），所以每次重建这三个值都会变，
`version` 素材和画面上的版本卡都要跟着改。

### ② profile/spark-cli.json

四个字段最常改：

```jsonc
"binary": { "path": "<仓库>/bin/spark", "build": "make build" },
"command_families": ["git", "hub", "magic", "script", "docs", "witr", "version", "completion"],
"quick_commands": [["git","batch-clone"], ["hub","registry"], ...],   // 逐条跑 --help 核存在性
"assets": { "<素材名>": { "command": [...], "capture": {...}, "crop": {...} } }
```

`quick_commands` 是**速查卡上那几条命令**的机器可核对版本：核对器会逐条跑 `<cmd> --help`，
跑不存在的立刻红。README 改了优先级，这里的清单要跟着改。

### ③ profile/facts.json

事实清单是画面上每句话的「可执行断言」。写法：

```json
{
  "id": "command_families",
  "on_screen": "命令族：git/hub/magic/script/docs/witr/version/completion",
  "where": "S05 架构图",
  "check": { "type": "command", "command": ["--help"], "expect_all": ["…"] }
}
```

四种检查类型：`command`（跑一条命令）、`file`（读仓库里一个文件）、
`quick_commands`（逐条跑 profile 里的子命令）、`manual`（机器核不了，人工确认）。

**把「命令族」写成一段连续文本，比逐个名字查更严**：

```jsonc
"expect_all": ["Available Commands:",
  "  completion  Generate the autocompletion script for the specified shell\n  docs        …\n  git         …\n  help        …\n  hub         …\n  magic       …\n  script      …\n  version     …\n  witr        …"]
```

逐个名字查只能发现「少了一个族」，写成连续的一段就能发现「多了一个族」——
比如 `repo`/`skill` 这种被删掉又冒回来的命令，会把中间的行号挤开，整段就配不上了。

**片子里推的命令，README 必须也写着一份**。加一条 `file` 检查把两者锁住：

```jsonc
{ "id": "readme_priority",
  "check": { "type": "file", "path": "README.md",
             "expect_all": ["spark git batch-clone", "spark hub registry", "…"] } }
```

这样 README 以后改了优先级，这条事实会红，片子不会再悄悄落后。

### ④ 改镜头代码（shots_spark.js）

这是最容易出静默错误的地方。三类东西要改：

**a) 标注用的真实输出行**（`L_HELP` / `L_VER`）：照着新素材的真实输出抄。
**b) 标注指向的行号**（`underline(ctx, d, c, k, n, …)` 的 `k`）：输出少一行，后面所有行号都前移。
**c) 画面上的文案**：`FAMS` / `QUICK` / 标题 / 能力标注。

素材改名要**三处同步**：profile 的 `assets` key、镜头的 `CARD` 表、镜头的 `term()` 引用。
少改一处，裁剪自检会拦下来（它比对 profile 和 CARD 表），但 `term()` 引用错了不报错——**画面上就是空白**。

### ⑤ 改配音稿（vo.json）

短句是按中文标点切出来的（`tools/syl.py:37`）：

```python
re.split(r'(<#[\d.]+#>|[，。；：？！、]|……)', t)
```

镜头里的 `ph('Sxx', k)` 取的就是**第 k 个短句的开始时刻**（`web/core.js:263`）。
所以：

- **每镜短句数变了，镜头里的 `ph()` 索引就得跟着改**；
- `en` 数组的长度必须等于中文短句数（一对一）；
- 短句数最好**保持不变**——只换措辞，不改句数，索引就不用动。

### ⑥ 重录素材

```bash
project/.venv/bin/python skills/cli-intro-video/scripts/pipeline.py \
  --profile profile --project project --only record --record
```

录完必须做两件事：

1. **抄网格几何**：`project/web/img/<素材>/meta.json` 里 `cell` 的四个数
   （`cw`/`ch`/`pad_x`/`top`）抄进镜头代码顶部的常量。别手算——素材文本区两侧有内边距，
   用名义值会让裁剪框超出素材边界，字被拉宽、标注线整体偏几个百分点。裁剪自检会逐个比对。
2. **同步一次**：`project/.venv/bin/python project/tools/timeline.py`。
   `web/project.js` 里的序列帧清单是扫描 `web/img/*/` 得来的快照，
   帧数变了它就过期，页面会按旧帧号去加载已经不存在的图片，渲染一启动就白屏。

---

## 3. 六个坑（都实测踩过）

### 坑一：短句索引平移是静默的

`core.js:263` 写的是 `p[Math.min(k, p.length - 1)]`——**越界不报错**，只是悄悄夹到最后一个短句。
表现是「画面上的动作比配音晚一拍」，很难看出来。

**改完配音先数一遍**：

```bash
python3 - <<'PY'
import json, re
SPLIT = re.compile(r'(<#[\d.]+#>|[，。；：？！、]|……)')
d = json.load(open('video/project/script/vo.json'))
for sc in d['scenes']:
    n = len([x for x in SPLIT.split(sc['text']) if x and not SPLIT.fullmatch(x)])
    print(sc['id'], '中文', n, '句 / en', len(sc['en']), '条',
          '✓' if n == len(sc['en']) else '✗')
PY
```

（`video/docs/studio-plan.md` 的 P1 计划把这个检查做成 `check_copy.py` 接进流水线，
到时候就不用手工数了。）

### 坑二：标注行号会整体平移

`spark --help` 的能力条从 4 条变 3 条，`Available Commands:` 就从第 10 行挪到第 9 行。
镜头里的 `underline(ctx, d, c, 10, …)` 和 `rowAt(d, c, 10, …)` 都要改成 9。
**下划线会画错地方，但画面不会报错**——一眼扫过去很难发现。

### 坑三：裁剪列数不够，体检量不到

裁剪范围里有 72 列的 `completion` 行，竖版裁 58 列就会把它切掉。
**体检是量图片里的字的，切掉的字它看不见**，所以只有裁剪自检能拦。

裁剪自检还会比对 profile 的 crop 和镜头 `CARD` 表，两边必须一致；
并且报「最宽一行 N 列」，列数要 ≥ N。

### 坑四：素材改名漏改 `term()`

裁剪自检比对的是 profile 和 `CARD` 表，**不检查 `term()` 里的素材名**。
名字写错，画面上那块就是空的，而所有自检都绿。

### 坑五：配音的读音错了，ASR 查不出来

「一行命令」该读 háng，TTS 读成 xíng——**画面上写着「一行命令」，声音说「一兴」，
观众一听就发现不对**。但 `tts.py` 的自动读音核对完全无感：它拿 ASR 转写跟稿子比，
而转写只会把字还原成「行」，háng 和 xíng 都写成「行」，**转写分辨不了读音**。

改法是换一种没有歧义的同义说法（「一行命令」→「一条命令」），
**不要用 `tts_fix` 硬掰**：字幕取自 `vo.json`，不套 `tts_fix`，
只换 `tts_fix` 会变成「声音说一条、字幕写一行」。

检查交给 `scripts/check_pron.py`（期望读音表在 `profile.pronunciation.rules`），
详见[改片手册（二）](film-refresh-io.md#6-配音是怎么生成的)。

### 坑六：别拿旧二进制的结果当结论

2026-11-22 这次，`facts.py` 报 `capabilities` 不符，第一反应是「事实写错了」。
实际是 `profile.binary.path` 指的二进制是前一天的，`spark --help` 还是重构前的三条能力。
**先确认二进制是新的，再看事实写得对不对。**

---

## 4. 一条命令跑完

```bash
cd video
project/.venv/bin/python skills/cli-intro-video/scripts/pipeline.py \
  --profile profile --project project --final --format all
```

| 步骤 | 做什么 | 不通过会怎样 |
|---|---|---|
| facts | 跑每条事实的来源，逐条比对 | 退出码 1，**不渲染** |
| crop | 核裁剪范围、profile 与 CARD 表一致、几何常量一致 | 退出码 1，**不渲染** |
| record | 按 profile 重录终端素材（要加 `--record`） | 退出码 1 |
| sync | 重建时间线与 `web/project.js` 的帧清单 | 退出码 1 |
| render | 渲染并体检（版面、字幕、响度、空帧、运动量） | 体检有硬伤就按报告改 |
| deliver | 打印成片事实，更新 `out/交付核对.md` | — |

**只想看效果、不想渲整片**：

```bash
project/.venv/bin/python project/tools/stills.py S02,S04,S05,S06     # 横版，每镜三帧
project/.venv/bin/python project/tools/stills.py 竖版 --format 9x16 S02@0.6,S04@0.6
```

直接从网页取帧，秒级出图，用来核对排版和文案最快。
`--format 9x16` / `1x1` 一定要各看一遍——三种画幅的裁剪范围不一样，
横版没问题不代表竖版没问题。

---

## 5. 本次实录（2026-11-22）

`4a7db1f` 之后，画面上有 4 处已经不存在的东西：

| 位置 | 原来写的 | 改成 |
|---|---|---|
| S02 能力标注 | 初始化远程 / 加子模块 | 批量更新仓库 / 扫描登记与克隆项目 / 执行自定义脚本（3 条） |
| S04 终端素材 | `spark repo --help`（命令已删） | `spark hub registry --help` |
| S05 标题与卡片 | 「十个命令族」，含 repo / skill | 「八个命令族」，8 张卡排 4×2 |
| S06 速查卡 | `spark repo scan` / `spark skill list` | README 优先级里的 5 条 |

改完的事实核对：**12 条通过，0 条不符**（`version` / `capabilities` / `command_families` /
`quick_commands` / `hub_two_catalogs` / `hub_collections_catalog` / `readme_priority` 等）。

三个画幅的版面预检也全过。第一次改完片长从 52.5 秒变成 **55.0 秒**（配音变长，voice 模式时间轴跟着走），
体检按 ±10% 判定，差 +4.8% 仍然通过。后来把「一行命令」改成「一条命令」重录配音，
片长又回到 **52.5 秒**，正好等于 `project.json` 的 `target_sec`。
