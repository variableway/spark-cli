# cli-video Skill 演进计划

写给「这套东西能不能一直用下去、怎么改内容、怎么重生成、引擎能不能信、接下来先做哪一步」。

下面每条结论都在本工程里核过，核法写在结论后面。要复现可以照着跑。

---

## 0. 结论速览

| 问题 | 结论 | 依据 |
|---|---|---|
| 能不能当整体的 cli-video skill | **能，但差一块**：SKILL.md 完整，缺的是「迭代已有片子」这条主路径 | `skills/cli-intro-video/SKILL.md` 的 Procedure 只有「从零起一个工程」 |
| 素材层是自动生成的吗 | **是**，但由 `profile` 的 `assets` 段驱动，**不由 `facts.json` 驱动** | `scripts/record_terminal.py` 读 `profile/<name>.json` 的 `assets.<名>.command` + `capture` |
| 改 `facts.json` 会让素材跟着变吗 | **不会**。`facts.json` 是核对清单，不是素材的生成源 | `scripts/facts.py` 只读它做比对，从不写它 |
| `spark-cli.json` 依据什么生成 | `scaffold.py` 起一份**带括号占位符的骨架**，之后手工填；不是从任何东西推出来的 | `scripts/scaffold.py` 的 `write_profile()` |
| 改文案难在哪 | 文案有**三个副本**，彼此没有校验；改配音稿会平移短句序号，画面跟着错位 | 实测 6 个镜头，短句数 == `en` 条数 == `ph()` 索引范围 |
| 改内容要不要整片重渲 | 分情况：改镜头代码只重渲那一个镜头；改配音/时间线/素材 → 整片 | `project/tools/render.py` 的分段指纹 |
| 引擎层有 hardcode 吗 | **没有项目专属的**。只有三类通用常量，且全部可被 `project.json` 覆盖或按片型缩放 | `grep -rn "spark-cli" skills/lucid/template/` 零命中 |
| 扩展方式 | **命令先行，SKILL 跟上**：先把一致性检查变成命令，再把流程写进 SKILL.md | 见第 6 节 |

---

## 1. 现在这套是什么

两层 Skill 加一层项目数据：

```
profile/     声明的真相：工具是谁、要录哪几段素材、画面上有哪些事实
   ↓
skills/cli-intro-video/scripts/   工作流：录素材 → 核对事实 → 裁剪自检 → 渲染 → 交付
   ↓
project/web/shots_spark.js        镜头：把素材画成画面（唯一的项目专属代码）
   ↓
skills/lucid/template/            引擎：逐帧渲染 → 合成 → 体检 → 交付核对
```

分工是清楚的，而且写进了 SKILL.md：`lucid` 负责「画面好不好看」，`cli-intro-video` 负责「画面里的是不是真的」。

**作为 skill 已经合格的部分**：`name` / `description` / `triggers` / 反例声明、Inputs to collect、
九步 Procedure、Output contract、Failure handling、Examples、Windows 平台说明，
外加 6 个脚本和一条 `pipeline.py` 把六步串起来。

**还差的那一块**：SKILL.md 的 Procedure 讲的是「给一个新工具从零做一支片」。
真实使用里第二遍、第三遍是**同一支片要改**——改说法、改文案、换工具版本、加一个画幅。
这一维在 SKILL.md 里一个字都没有，脚本里也没有对应入口。
第 3、4、6 节都围绕它展开。

---

## 2. 素材层：自动生成，但不由 facts.json 驱动

### 素材是怎么来的

```
profile/<name>.json 的 assets.<名>.command   要跑哪条命令
                          assets.<名>.capture  跑多大、多快、录多久
                    ↓
        scripts/record_terminal.py            真的执行一次，原样采集 stdout/stderr
                    ↓
project/web/img/<名>/0001.png … N.png         无损 PNG 帧序列
project/web/img/<名>/meta.json                真实网格（cell.cw / ch / pad_x / top）
```

四段素材的实测值（来自各自 `meta.json`）：

| 素材 | 帧数 | 时长 | 尺寸 |
|---|---|---|---|
| help | 94 | 6.288 s | 1250×776 |
| version | 37 | 2.457 s | 1250×262 |
| repo | 148 | 7.376 s | 1250×957 |
| skill | 132 | 6.576 s | 1250×926 |
| **合计** | **411** | | |

### 三件事要分清

| 文件 | 是什么 | 谁生成 | 改了它会怎样 |
|---|---|---|---|
| `profile/<name>.json` | **素材的生成源**——声明要录哪条命令、录多大 | `scaffold.py` 起骨架，之后手工填 | 要重录才会变 |
| `profile/facts.json` | **核对清单**——画面上写什么 + 怎么核它是真的 | `scaffold.py` 起骨架，之后手工填 | **素材一点不变**；只影响 `facts.py` 的核对 |
| `project/web/img/<名>/` | 素材本体 | `record_terminal.py` 真跑命令产出 | — |

换句话说：**`facts.json` 变了，素材不会跟着变**。它俩是并列关系，不是上下游。
`facts.json` 管的是「画面上写的『v0.4.0』是不是真的」，素材管的是「画面里那屏终端输出是不是真的」。

`facts.json` 里没有的画面事实（镜头里的一句标题、卡片上的一行字）也一样不会进素材——
素材只反映命令的实际输出。

### `spark-cli.json` 是怎么来的

`scaffold.py` 的 `main()` 依次写出三样东西：

```
write_profile()  → profile/<name>.json   骨架，字段值是「（……）」这样的括号占位符
write_facts()    → profile/facts.json     骨架，一两条示例事实
write_shots()    → project/web/shots_*.js 镜头骨架
```

**骨架只起结构，数字全留空**——不复制现成工程的真实值，也不从别处推导。
要得到能用的 `spark-cli.json`，得靠人或 agent 把占位符换成真实内容：
二进制路径、构建命令、URL、命令族、`quick_commands`、每段素材的 `capture` 与 `crop`。

所以它是**手维护的声明文件**，不是自动生成的产物。

---

## 3. 改文案 / 改说法：难在哪

### 三个副本

一段话要出现在三个地方，三处各写各的：

| 副本 | 在哪 | 谁看它 |
|---|---|---|
| 配音稿 | `project/script/vo.json` 的 `text` | 观众（听）+ 引擎（切短句） |
| 画面中文案 | `project/web/shots_spark.js` 里的字面量 | 观众（看） |
| 事实描述 | `profile/facts.json` 的 `on_screen` | 核对器（比对） |

### 短句序号这条暗线

`vo.json` 的 `text` 会被 `tools/syl.py` 按中文标点切成短句：

```python
re.split(r'(<#[\d.]+#>|[，。；：？！、]|……)', t)   # 逗号、句号、顿号、分号、冒号、问号、叹号
```

`tools/build_timeline.py` 把切出来的短句配上真实起止时刻写进 `timeline.json`，
镜头代码再用 `ph('S03', 2)` 取第 2 个短句的起始时刻（`web/core.js:263`）：

```js
const ph = (id, k) => { const p = TL.scenes[id].phrases; return p[Math.min(k, p.length - 1)].t0; };
```

**实测（本轮逐个镜头核过）**：6 个镜头的「中文标点切出的短句数」==「`en` 译文条数」==「`ph()` 用到的索引范围」，
三者逐个相等：

| 镜头 | 短句数 | `ph()` 索引 | `en` 条数 |
|---|---|---|---|
| S01 | 2 | 0,1 | 2 |
| S02 | 6 | 0–5 | 6 |
| S03 | 4 | 0,3 | 4 |
| S04 | 4 | 0–3 | 4 |
| S05 | 6 | 0–5 | 6 |
| S06 | 3 | 0–2 | 3 |

### 由此产生的三个真实故障

1. **改配音稿 → 短句数变 → 索引平移。**
   把 S02 的「更新仓库、初始化远程、加子模块、跑脚本」改成「更新仓库、初始化远程、加子模块和跑脚本」，
   顿号少一个，短句从 6 条变 5 条。`ph('S02', 5)` 不会报错——`Math.min(k, p.length - 1)` 把它**夹到最后一个短句**，
   于是第五、六个画面元素挂到了同一句配音上。静默错位。

2. **画面中文案是另一份副本，没有任何检查。**
   `shots_spark.js` 里 `'每天重复十遍的命令'` 和 `vo.json` 里 `'重复十遍的命令，交给一个工具。'`
   是同一句话的两次手写。改了配音稿忘了改镜头代码，两个画面就说了不一样的话。

3. **英文译文条数不匹配会被拦住——这是唯一被机器守住的一条。**
   `build_timeline.py` 的 `check_langs()` 会检查 `en` 条数 == 中文短句数，不等就打印出
   哪条该配哪句并停下。所以「改了中文忘了改 `en`」会立刻报错，
   但「改了中文、也改了 `en`、画面索引没跟着改」**不会**。

### 现在改一句话要动几处

| 只改配音（观众听到的不变） | 只改画面字（观众看到的变） | 两者都改 |
|---|---|---|
| `vo.json:text` | `shots_spark.js` 字面量 | 两个都改 |
| `vo.json:en`（条数不变时） | `facts.json:on_screen`（若涉及事实） | `facts.json:on_screen` |
| 重跑 `tts.py full` → `timeline.py` → 渲染 | `facts` → 渲染 | 全套 |
| — | — | 还要自己核 `ph()` 索引 |

这就是「一次性成型」的由来：**改的成本是重建的成本**，没有中间档。

---

## 4. 改内容 vs 重新生成

`project/tools/render.py` 按段做指纹，指纹没变的段直接复用上次的结果。指纹 =
**公共部分** + **这一段在画的镜头所在文件的内容**。

- 公共部分：`web/` 下除 `shots_*.js` 外的内容 + `project.json` + `timeline.json`
  + 页面登记的 SHAKES/FLASH/CUTS/FAST + 档位参数（帧率、尺寸、运动模糊、CRF）
- 段内部分：这一段时间实际在画的每个镜头（按 pre/post 与转场算出的绘制范围）所在文件的内容

结论：**改一个镜头文件，只重渲它覆盖的那些段；改公共文件或时间轴，整片重渲。**

| 改了什么 | 必须重跑 | 重渲范围 | 代价 |
|---|---|---|---|
| 镜头里的一个字面量 | `facts`（若涉及事实）→ `render` | 只有那个镜头覆盖的段 | 秒级 |
| 镜头代码的几何 / 布局 | `crop` → `render` | 那个镜头覆盖的段 | 秒级 |
| `vo.json` 的 `text` | `tts.py full` → `timeline.py` → `facts` → `render` | **整片**（timeline.json 变了） | 分钟级 |
| `vo.json` 的 `en` | `timeline.py` → `render` | **整片**（译文进 timeline.json） | 分钟级 |
| `facts.json` | `facts` | 不影响渲染 | 秒级 |
| `profile` 的 `assets.<名>.capture` | `record` → `sync` → **重抄几何常量** → `render` | **整片** | 十分钟级 |
| 裁剪范围（`CARD` 表 ↔ profile 两边） | `crop` → `render` | 受影响的镜头 | 秒级 |
| `project.json`（画幅 / 片型 / fps） | `timeline.py` → `render` | **整片** | 分钟级 |
| 引擎升级（换 `template/`） | `sync` → `crop` → `render` | **整片** | 分钟级 |

两条容易踩的连带：

- **重录素材后必须重抄几何常量。** `meta.json` 的 `cell.cw/ch/pad_x/top` 变了，
  `shots_spark.js` 顶部的 `COLW/CH/PADX/TOP` 不跟着改，标注线就整体偏。
  `check_crop.py` 会拦（容差 0.02 像素），但它只报错，不替你改。
- **重录素材后必须 `sync`。** `web/project.js` 的帧清单是扫 `web/img/*/` 得到的快照，
  不刷新就白屏。流水线的 `sync` 步做这件事。

所以「重新生成」的重启成本是分级的：**改画面字 → 秒级；改配音 → 分钟级；改素材 → 十分钟级。**
现在的问题不在渲染速度，在于改配音必须重新配音，而重新配音必须重新对时间线，
于是连画面字的小改也被迫走整条链——因为文案没有单一真相源。

---

## 5. 引擎层有没有 hardcode

### 结论

**没有项目专属的 hardcode。** 引擎对这支片一无所知，它只认 `project.json`。

```bash
$ grep -rn "spark-cli\|spark_cli\|SparkCLI" video/skills/lucid/template/
（零命中）
```

### 只有三类通用常量，全部是设计而非偷懒

| 常量 | 在哪 | 性质 |
|---|---|---|
| `canvas` 默认 1920×1080 | `tools/common.py:117`、`web/core.js:35` | **默认值**，`project.json` 的 `formats` 一写就覆盖 |
| `U = min(W, H) / 1080` | `web/core.js:38` | 1080p 是**版面参考单位**：字号、间距、圆角都按短边等比缩放，竖版方版自动跟着变 |
| 片型阈值（字太小 = 短边 × 0.022；抖动门限 promo 2.0 / 其他 3.0） | `tools/layout.py`、`tools/checkup.py:470` | 按 `project.json` 的 `genre` 走 |
| 系统字体候选路径 | `tools/common.py:105`、`tools/assets.py:1068` | **平台级**，找系统里装了什么字体 |

引擎读项目配置的入口是统一的：

```python
# tools/common.py
def formats(cfg=None):
    f = cfg.get('formats')            # project.json 里写什么就用什么
    ...
```

```js
// web/core.js
const _SIZE = (FMT && PROJECT.formats && PROJECT.formats[FMT]) || PROJECT.canvas || { w: 1920, h: 1080 };
```

### 真正的硬编码在哪

不在引擎层，在**项目层**：

| 硬编码 | 在哪 | 为什么不能消掉 |
|---|---|---|
| 几何常量 `COLW=13.1803 / CH=30.1871 / PADX=18.7075 / TOP=51.0204` | `shots_spark.js` 顶部 | 素材网格的实测值，只能抄 `meta.json` |
| `ph('S02', 5)` 这类短句序号 | `shots_spark.js` | 时间对齐点，跟着配音稿的切句走 |
| 画面中文案字面量 | `shots_spark.js` | 见第 3 节——这是**应该被消掉**的一处 |
| `CARD` 表的裁剪范围 | `shots_spark.js` | 与 `profile` 的 `crop` 两边互为镜像，`check_crop.py` 对照 |

前三个里，只有**画面中文案**是纯粹的重复劳动，值得收口；
几何常量和短句序号是「实测量」，必须跟着素材和配音走，收不掉。

### 边界一句话

> 引擎管「怎么画」，profile 管「画什么真东西」，`shots_spark.js` 管「怎么摆」。
> 要改引擎 → 改 `~/.minimax/v2/plugin-cache/.../lucid/`，再同步进 `video/skills/lucid/`；
> 要改内容 → 只动 `profile/`、`vo.json`、`shots_spark.js`。

---

## 6. 扩展方式：分阶段还是加命令

**两者都要，但分工不同，不能互相替代。**

- **命令**解决的是「把现在靠人记的约束变成机器可执行的检查」。
- **阶段**解决的是「什么时候用、按什么顺序、怎么算做完了」。

只有命令没有阶段：使用者面对一排 `check_copy.py` / `crop` / `facts`，不知道该跑哪个；
只有阶段没有命令：写了「改文案要同步三处」，但没人保证他真的同步了。

### 建议的三阶段

每阶段一个可交付物 + 一条验收标准，一次只做一段。

---

#### 阶段一：把一致性变成检查（只读，不改任何数据源）

新增 `scripts/check_copy.py`，并在 `pipeline.py` 里加 `copy` 步（排在 `facts` 之后、`crop` 之前）。

它查三件事：

1. **`ph()` 索引有效性**——镜头代码里每个 `ph('Sxx', k)` 的 `k` 必须落在该镜头短句数范围内，
   且**每个短句都至少被引用一次**（漏引说明有一段配音没有对应画面动作）。
2. **三副本一致性**——`vo.json` 的 `text`、`shots_spark.js` 里同镜头的字面量、
   `facts.json` 的 `on_screen` 指向同一个意思。做法：把镜头里的中文字面量抽出来，
   与该镜头的短句做词面比对，差异列出来人工确认（先只报告，不拦）。
3. **`en` 条数 == 短句数**——引擎已经查了，这里再查一遍是为了给出更友好的提示。

同时在 `references/pitfalls.md` 补一条：**改配音稿会让短句序号平移**。

验收：`pipeline.py --only copy` 在当前工程上通过；把 S02 的短句数人为改错，命令报错并指出是哪个镜头。

风险：低。只读。

---

#### 阶段二：文案收成单一真相源

把画面中文案从 `shots_spark.js` 的字面量挪到一个数据文件——建议放 `profile/<name>.json` 的 `copy` 段：

```json
"copy": {
  "S01": {
    "title1": "每天重复十遍的命令",
    "title2": "交给一个工具"
  }
}
```

`shots_spark.js` 改成引用：`copy('S01', 'title1')`。

**为什么放 profile 而不是 vo.json**：profile 已经承担「声明的真相」这个角色，
而 `vo.json` 是配音稿（由 `tts.py` 消费，格式受引擎约束）。文案是「画面上写什么」，
归 profile 更顺；`facts.json` 的 `on_screen` 也可以由它派生。

验收：改 profile 里的文案 → 重跑 `facts` → 画面自动跟着变；
`check_copy.py` 不再报三副本不一致。

风险：中。要一次性改 `shots_spark.js` 的全部字面量，改完重新出片对齐。

---

#### 阶段三：改文案走一条命令

新增 `scripts/rewrite_copy.py`（或给 `pipeline.py` 加 `--sync-copy`）：

```
改文案 → 自动重算短句 → 校验 ph() 索引 → 重跑 tts → 重跑 timeline → 增量渲染
```

它要解决的是第 4 节最后那句：「因为文案没有单一真相源，改配音就必须重配音，
于是连画面字的小改也被迫走整条链」。收口之后，**改画面字**和**改配音**才走得通两条不同的路：

- 只改画面字 → profile → `facts` → 渲染（秒级，镜头级重渲）
- 改配音 → vo.json → `tts full` → `timeline` → 渲染（分钟级，整片）

验收：改一句画面文案，30 秒内看到新画面；改一句配音，3 分钟内拿到新成片。

风险：高。要动 `tts.py` / `build_timeline.py` 的调用顺序。

---

### 要新增 / 要改造的命令清单

| 命令 | 类型 | 作用 | 阶段 |
|---|---|---|---|
| `check_copy.py` | 新增 | 查 `ph()` 索引、三副本、`en` 条数 | 一 |
| `pipeline.py` 的 `copy` 步 | 新增 | 把上面的检查接进流水线 | 一 |
| `pipeline.py --only copy` | 新增 | 单跑一致性检查 | 一 |
| `pipeline.py --sync-copy` | 新增 | 改完文案一条龙（重算 → 校验 → 配音 → 时间线 → 渲染） | 三 |
| `profile/<name>.json` 的 `copy` 段 | 数据 | 画面文案的单一真相源 | 二 |
| `shots_spark.js` 的 `copy()` 引用 | 代码 | 镜头不再写字面量 | 二 |
| `facts.json` 的 `on_screen` 派生 | 数据 | 减少第三份手写 | 二（可选） |
| `tts.py` / `build_timeline.py` | 改造 | 让「只改画面不重配音」成立 | 三 |

---

## 7. 建议的落地顺序

一次一件事，每件都能单独验证、单独提交：

1. **`check_copy.py` + `pipeline.py` 的 `copy` 步**（阶段一）
   —— 纯增量，不改任何现有数据源，先把「三副本不一致」和「`ph()` 索引错位」暴露出来。
2. **SKILL.md 补一节「迭代已有片子」**（阶段一尾）
   —— 把「改哪句话要动哪几处」写成流程；这一步不需要等阶段二，
   因为阶段一的检查命令已经把机器守不住的地方写清楚了。
3. **`profile` 的 `copy` 段 + `shots_spark.js` 改造**（阶段二）
   —— 收口。做完之后「改文案」才真正变成一条命令能办的事。
4. **`rewrite_copy.py`**（阶段三）

第 1、2 步做完，这套东西就从「一次性成型」变成「可以一直用」。
第 3、4 步做完，它才配得上叫一条 Skill 而不是一段脚本。

---

## 附：本轮怎么核的

| 结论 | 核法 |
|---|---|
| 素材由 profile 驱动，不由 facts 驱动 | 读 `scripts/record_terminal.py` 与 `scripts/pipeline.py` 的 `step_record`；`scripts/facts.py` 全程只读 facts.json |
| `spark-cli.json` 是骨架占位符 | 读 `scripts/scaffold.py` 的 `write_profile()`：每个字段值都是 `（……）` |
| 短句数 == `en` 条数 == `ph()` 索引 | 脚本复算 `tools/syl.py` 的切句规则，对 6 个镜头逐个比对 |
| 渲染指纹的范围 | 读 `project/tools/render.py` 的 `common_hash()` 与 `plan()`，以及文件头注释 |
| 引擎无项目专属硬编码 | `grep -rn "spark-cli\|spark_cli\|SparkCLI" video/skills/lucid/template/` 零命中；`canvas`/`formats`/`fps`/`genre` 全部读 `project.json` |
| `en` 译文进 timeline.json | 读 `project/tools/build_timeline.py:231`：每条短句带各语言译文，`timeline.json` 是公共指纹的一部分 |
