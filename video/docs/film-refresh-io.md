# 改片手册（二）· 输入输出结构与手动流程

配套：[改片手册（一）](film-refresh-playbook.md)——改片的**顺序**和**坑**。
这一篇讲**结构**：每个文件是什么、谁产出谁消费、改完之后按什么路径重跑。

本文所有结论都在本工程里核过。涉及读音的部分都做了对照实验（见 §6）。

---

## 1. 先把名词说清楚

### S01、S02……是什么

**镜头号**（scene id）。一支 52.5 秒的片子切成 6 段，每段一个镜头，编号 S01–S06。

同一个编号在四个地方同时出现，改一处就得想清楚另外三处：

| 地方 | S03 长什么样 | 作用 |
|---|---|---|
| `project/script/vo.json` | `{"id": "S03", "text": "…", "en": [...]}` | 这一镜的配音稿 |
| `project/web/shots_spark.js` | `SHOT.S03 = function (ctx, t, S) { … }` | 这一镜的画面代码 |
| `project/project.json` → `chapters` | `{"id": "demo", "label": "真实命令", "scenes": ["S03", "S04"]}` | 章节把镜头分组（钩子／它是什么／真实命令／为什么用／速查与落版） |
| `project/timeline.json` → `scenes` | `{"S03": {"t0": 16.25, "t1": 21.87, "phrases": [...]}}` | 这一镜在时间轴上的位置和逐句时刻 |

**短句（phrase）**：一段配音稿按中文标点切开的句子（`tools/syl.py:37`），
切句规则是 `re.split(r'(<#[\d.]+#>|[，。；：？！、]|……)', text)`。

镜头里的 `ph('S03', 2)` 取的就是**第 2 个短句的开始时刻**（`web/core.js:263`）。
所以**短句数一变，镜头里的 `ph()` 索引就平移**，而 `core.js:263` 写的是
`p[Math.min(k, p.length - 1)]`——**越界不报错**，只是悄悄夹到最后一个短句，
表现是「画面上的动作比配音晚一拍」。这是这套流程里最容易出的静默错误。

### 其余几个词

| 词 | 是什么 |
|---|---|
| **素材** | 终端真的跑一遍命令，把输出渲染成无损 PNG 帧序列（`web/img/<名>/`）。静帧入库，帧序列不入库 |
| **profile** | `profile/spark-cli.json`——这支片讲谁：二进制、命令族、素材怎么录、每种画幅裁多少 |
| **facts** | `profile/facts.json`——画面上每句话的**可执行断言**，渲染前逐条比对 |
| **网格** | 素材的字符网格（列宽/行高/左内边距/首行顶），记在 `web/img/<名>/meta.json` 里，镜头代码要照抄 |
| **裁剪** | 从素材里切出画面上要显示的那一块（行区间 + 列区间），profile 和镜头 `CARD` 表两边必须一致 |

---

## 2. 输入结构

**手写的只有 5 个文件**，其余全是工具生成：

| 文件 | 谁写 | 改它会影响什么 |
|---|---|---|
| `profile/spark-cli.json` | 人 | 命令族、速查卡清单、素材录制参数、裁剪范围、二进制路径、**多音字期望读音表** |
| `profile/facts.json` | 人 | 事实核对的内容。少一条，屏幕上就可能多一句没人核过的假话 |
| `project/script/vo.json` | 人 | 配音稿（`text` 中文 / `en` 逐句英译 / `tts_fix` 同音字替换） |
| `project/web/shots_spark.js` | 人 | 六个镜头的画面代码：字面量、标注行号、卡片、几何常量 |
| `project/project.json` | 人 | 片型、画幅、主题、音色、章节、目标时长 |

**生成的（不要手改，重跑工具会覆盖）**：

| 文件 | 谁生成 |
|---|---|
| `project/timeline.json` | `tools/timeline.py`——按配音的真实时刻排的时间轴 |
| `project/web/timeline.js` | 同上，页面用的那份 |
| `project/web/project.js` | 同上，工程配置 + **素材帧清单**（扫描 `web/img/*/` 得来的快照） |
| `project/web/index.html` | 同上，被补过 `<script>` 标签 |
| `project/audio/narration.mp3/.wav` | `tools/tts.py full` |
| `project/audio/narration.json` | 同上，配音档案（音色/语速/时间） |
| `project/web/img/<名>/` | `scripts/record_terminal.py`——真跑命令录的帧序列 |
| `project/out/*.mp4`、`out/spark.srt`、`out/交付核对.md` | `tools/render.py`、`tools/deliver.py` |
| `project/frames/_view/` | 体检报告、静帧、总览图 |

**只读的两块**：`skills/lucid/template/`（引擎）和 `skills/cli-intro-video/scripts/`（工作流）。
工程里是它们的副本；原件在用户目录，改脚本先改原件再同步回来。

---

## 3. 输出结构

一次完整刷新（改文案 → 成片）的产物链：

```
vo.json ──tts.py full──▶ audio/narration.mp3
                            │
profile/*.json ─────────────┤
shots_spark.js ─────────────┤
web/img/<素材>/ ────────────┤
                            ▼
                     tools/timeline.py
                            │
      ┌─────────────────────┼─────────────────────┐
      ▼                     ▼                     ▼
timeline.json          web/timeline.js        web/project.js
（入库）               （入库）                （入库）
                            │
                            ▼
                     tools/render.py
                            │
      ┌─────────────────────┼─────────────────────┐
      ▼                     ▼                     ▼
out/spark_16x9.mp4   out/spark_9x16.mp4    out/spark_1x1.mp4
   （不入库）            （不入库）             （不入库）
      └─────────────────────┼─────────────────────┘
                            ▼
              tools/deliver.py → out/交付核对.md
              tools/checkup.py → frames/_view/报告.md
```

**入库的只有 4 个生成物**：`timeline.json`、`web/timeline.js`、`web/project.js`、
`audio/narration.json`（加上 5 个静帧）。成片、字幕、交付核对、体检报告都不入库——
它们是产物，重新跑一次就有。

---

## 4. 素材已存在时的手动流程

**核心判断：这次改动碰没碰「命令的输出」。**

| 改了什么 | 要不要重录终端素材 | 要不要重录配音 | 跑哪条路径 |
|---|---|---|---|
| 只改画面上的字（`shots_spark.js` 的字面量） | 否 | 否（配音稿没动） | `--stage shots` |
| 改了配音稿（`vo.json`） | 否 | **是** | `--stage voice` |
| 命令的输出变了（改了命令、加了子命令、版本号变了） | **是** | 否 | `--stage assets` |
| 全都变了 | 是 | 是 | `--stage all` |
| 只想看看有没有问题 | 否 | 否 | `--stage check` |

`scripts/refresh.py` 把这几条路径写死了：

```bash
cd video
# 只改画面字面量：门禁 → 渲染 → 交付核对（配音和素材都不动）
project/.venv/bin/python skills/cli-intro-video/scripts/refresh.py \
  --project project --profile profile --stage shots --final --format all

# 改了配音稿：重录配音 → 重建时间轴 → 门禁 → 渲染 → 交付核对
project/.venv/bin/python skills/cli-intro-video/scripts/refresh.py \
  --project project --profile profile --stage voice --final --format all

# 命令输出变了：重录素材 → 重建时间轴 → 门禁 → 渲染 → 交付核对
project/.venv/bin/python skills/cli-intro-video/scripts/refresh.py \
  --project project --profile profile --stage assets --final --format all

# 只跑门禁，什么都不改
project/.venv/bin/python skills/cli-intro-video/scripts/refresh.py \
  --project project --profile profile --stage check
```

加 `--dry-run` 只打印这一步要跑什么，不真跑。

**为什么要有这个**：`pipeline.py` 的步骤里**没有配音那一步**——配音是 `tts.py` 干的。
改了配音稿以后忘了补 `tts.py full`，就会拿旧配音渲出新画面，字幕和声音对不上，
而且所有门禁都绿。`refresh.py` 把「改了什么 → 跑哪几步 → 跳过哪几步」固定下来，
每跑一步都打印跳过了什么、为什么。

---

## 5. 跑之前检查什么

`refresh.py` 每次都会打印这张清单。前三条脚本能查，后面两条要人看：

| # | 检查 | 谁查 |
|---|---|---|
| 1 | 二进制是新的吗（profile 指的那个是改完源码之后构建的吗） | 人。**二进制比源码旧时，事实核对拦的是二进制，不是画面** |
| 2 | 每镜中文短句数 == `en` 数组长度 | 人（`refresh.py` 的跑前清单里给了片段） |
| 3 | 画面文案和配音稿对得上（改一句要改两处） | 人 |
| 4 | 多音字期望读音表覆盖了稿子里所有多音字 | `check_pron.py` |
| 5 | 命令的输出变了吗（变了才重录素材） | 人 |

门禁本身（自动，红了就停）：`facts.py`（事实）、`check_crop.py`（裁剪/几何/截字）、
`check_pron.py`（读音）。

---

## 6. 配音是怎么生成的

### 链路

```bash
cd video/project
./.venv/bin/python tools/tts.py full          # 合成整段配音 + 自动读音核对
./.venv/bin/python tools/timeline.py          # 按配音的真实时刻排时间轴
```

`tts.py full` 做四件事：

1. 把 `vo.json` 里六个镜头的 `text` 用 `<#gap#>` 连成整段（`tts_fix` 在这里替换同音字）；
2. 调 mcode-tools 的 TTS 合成（音色 `voice.voice_id`，语速 `voice.speed`），
   拿到词级时间后按停顿标记切开、补足停顿时长；
3. 自动转写一遍，和稿子逐句比对（英文词/数字/其他词三类差异）；
4. 存 `audio/narration.mp3`、`narration.wav`、`narration.json`。

`timeline.py` 再按这个音频的真实时刻，把六个镜头的逐句 `t0/t1` 排进 `timeline.json`。

**所以配音是时间轴的源头**：改一个字 → 重录配音 → 时间轴全变 → 画面事件跟着挪。
先改画面后改配音，顺序反了就会让 `ph()` 指向一个还不存在的短句。

### 读音错了怎么办

**症状**：画面上写着「一行命令」，声音读成「一兴命令」。

**为什么工具查不出来**：`tts.py` 的自动读音核对是拿 ASR 转写跟稿子比，
而转写只会把字还原成「行」——háng 和 xíng 都写成「行」，**转写分辨不了读音**。
（实测：对同一段音频，ASR 转写完全无感，只有问「这个字读什么音」才问得出差别。）

**方法**：换一种没有歧义的同义说法。

| 原写法 | 改成 | 为什么 |
|---|---|---|
| 一行命令 | **一条命令** | 「行」在「一行」里该读 háng，TTS 读成 xíng；「条」只有一个读音 tiáo，没有歧义 |

**不要用 `tts_fix` 硬掰**：字幕文本来自 `vo.json`（`tools/srt.py` 读的是
`timeline.json` 的 phrase text，**不套 `tts_fix`**）。只在 `tts_fix` 里换，
结果是「声音说一条、字幕写一行」——不一致的是字幕和画面，比原来还糟。

**代码**：`scripts/check_pron.py`

```bash
# 静态：扫出配音稿里所有多音字，和期望读音表对一遍（不联网，秒级）
python3 video/skills/cli-intro-video/scripts/check_pron.py \
  --project video/project --profile video/profile

# 动态：真的切出音频片段、问 AI 每个词实际读什么音，和期望值比
python3 video/skills/cli-intro-video/scripts/check_pron.py \
  --project video/project --profile video/profile --ask
```

**期望读音表是数据不是代码**，写在 `profile/spark-cli.json`：

```jsonc
"pronunciation": {
  "rules": [
    { "word": "重复", "char": "重", "pinyin": "chóng fù",
      "note": "重复十遍读 chóng；zhòng 是「重量」那个" },
    { "word": "一行", "char": "行", "pinyin": "yī háng",
      "note": "TTS 会读成 xíng，所以稿里避开这个词" },
    { "word": "命令行", "char": "行", "pinyin": "mìng lìng",
      "model_unreliable": true,
      "note": "模型会按「命令+行」的语义拆字，答成 mìng lìng háng；属于模型偏差" }
  ]
}
```

- `pinyin` 是**整词**读音，空格分音节。比对时去掉声调、连写后比音节
  （háng vs xíng 音节不同会被拦下；棵 vs 颗 音节相同，不会误报）。
- `model_unreliable: true` 的词条**不参与 `--ask` 判定**——AI 对它不可靠，人工听过是对的。
- 稿子里出现但规则表没覆盖的多音字，静态检查会报「未覆盖」，退出码 1，
  逼着把期望读音补上。

**模型的已知偏差（实测）**：音频问答模型问「命令行工具怎么读」会答
`mìng lìng háng gōng jù`（按「命令+行」的语义把 5 个字拆成 5 个音节）。
对照实验：**从文本合成的**同一段音频它也这么答，所以这是模型偏差，不是录音问题。
真正需要人工判断的场合，用 `--ask` 拿到结果后自己听一遍再定。

### 改完之后怎么重录重合成

```bash
cd video
# 1. 改 vo.json 的 text（配音稿）和 shots_spark.js 的字面量（画面），两处都要改
# 2. 静态查一遍多音字覆盖
project/.venv/bin/python skills/cli-intro-video/scripts/check_pron.py \
  --project project --profile profile
# 3. 重录配音 → 重建时间轴 → 门禁 → 渲染 → 交付核对
project/.venv/bin/python skills/cli-intro-video/scripts/refresh.py \
  --project project --profile profile --stage voice --final --format all
```

`--stage voice` 里已经串好了 `tts.py full` → `timeline.py` → `facts` → `crop` → `pron`
→ `render` → `deliver`，**不会重录终端素材**（命令输出没变就不该重录，那是十分钟级）。

改完只想看画面、不想渲整片：

```bash
cd video/project
./.venv/bin/python tools/stills.py S03,S04,S06          # 横版，每镜三帧
./.venv/bin/python tools/stills.py 竖版 --format 9x16 S03@0.6,S04@0.6
```

秒级出图，三种画幅都要看一遍——裁剪范围不一样，横版没问题不代表竖版没问题。
