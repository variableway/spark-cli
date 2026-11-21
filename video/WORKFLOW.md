# spark-cli 介绍片 · 工作流

52 秒的中文介绍片，三种画幅（16:9 / 9:16 / 1:1）从同一份工程导出。
画面里的每条命令、每个版本号、每个 URL 都是真的——这一点由事实核对器
在渲染前逐条核对，不是靠人记。

## 工具链在 Skill 里，工程只放项目数据

通用工具（录制素材、事实核对、裁剪自检、流水线）不放在这个仓库里，
放在 `cli-intro-video` Skill 里：

```
~/.minimax/agents/mavis/skills/cli-intro-video/
├── SKILL.md              什么时候用这套流程、怎么用
├── scripts/              record_terminal / facts / check_crop / pipeline / scaffold
└── references/           工作流详解、profile 字段说明、踩坑记录
```

一份工具只维护一处。下一个工具要做介绍片，写一份新的 profile 就行，
不用再抄一遍脚本。Skill 里的脚本对任何工程都能用。

## 目录

```
video/
├── profile/          这支片讲谁：工具元数据、素材录制参数、画面上的每个事实
│   ├── spark-cli.json    二进制怎么构建、命令、URL、命令族、每个素材的裁剪范围
│   └── facts.json        画面上出现的事实 → 它的来源和校验方式
├── project/          lucid 框架副本（保持原样，框架升级时可整体覆盖）
│   ├── project.json      片型、画幅、主题、配音
│   ├── script/vo.json    配音稿 + 逐句英译
│   ├── web/shots_spark.js 六个镜头的代码
│   └── tools/            lucid 自带的渲染、体检、交付脚本
├── assets/           素材原料（构建产物等，不进版本库）
└── out/              成片与交付核对（不进版本库）
```

`project/` 是 lucid 框架的副本，升级框架时整体替换即可；自己的代码只有
`project/web/shots_spark.js`，不会被覆盖。

## 一条命令跑完

```bash
cd video
SKILL=~/.minimax/agents/mavis/skills/cli-intro-video
project/.venv/bin/python $SKILL/scripts/pipeline.py \
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
SKILL=~/.minimax/agents/mavis/skills/cli-intro-video
project/.venv/bin/python $SKILL/scripts/record_terminal.py \
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
