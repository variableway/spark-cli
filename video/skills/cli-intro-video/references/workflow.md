# 完整工作流

从零到一个多画幅成片，中间每一步做什么、产出什么、怎么验。
细节字段看 `references/profile-schema.md`，踩过的坑看 `references/pitfalls.md`。

## 这套流程在框架里的位置

```
        ┌───────────── cli-intro-video skill（本层）─────────────┐
        │  scaffold · record_terminal · facts · check_crop      │
        │  profile 驱动：工具元数据 / 素材参数 / 裁剪范围 / 事实  │
        └────────────────────────┬───────────────────────────────┘
                                 │ 产出工程
        ┌────────────────────────▼───────────────────────────────┐
        │            lucid skill（下游层，代码视频框架）           │
        │  镜头代码 · 配音 · 时间线 · 音乐 · 渲染 · 体检 · 交付核对 │
        └────────────────────────────────────────────────────────┘
```

分工的关键：**上游层管「内容是不是真的」，下游层管「画面好不好看」**。
lucid 的体检量不了「画面上的版本号对不对」，也不管图片里的字有没有被切掉——
这两件事归上游，所以上游的工具要独立于 lucid，框架升级时不受影响。

## 阶段

### 0. 工具链就位

```bash
# lucid 模板的位置：先读 skill 拿到 Location，目录名带哈希
# 脚本会自己 glob 找，也可以显式指定
export LUCID_TEMPLATE=/path/to/skills/lucid/template

# 工程 Python 环境（lucid 的依赖）
cd project && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

依赖装在工程 `.venv` 里。不要装进系统 Python，不要把框架的插件目录复制进用户工程。

### 1. 起工程

```bash
python3 scripts/scaffold.py --dest ../mytool-video --name mytool \
  --title "My Tool" --binary /usr/local/bin/mytool --build "make build"
```

产出：

```
mytool-video/
├── profile/
│   ├── mytool.json     工具元数据（骨架，待填）
│   └── facts.json      事实清单（骨架，待填）
└── project/
    ├── project.json    lucid 片型配置
    ├── script/vo.json  配音稿
    ├── tools/          lucid 框架脚本
    └── web/shots_mytool.js   镜头代码骨架
```

### 2. 填 profile

先让被介绍的工具能跑：

```bash
cd mytool && make build && ./mytool --version
```

二进制路径写进 `profile/<name>.json` 的 `binary.path`。路径会失效（`/tmp` 会被清理），
所以 `binary.build` 要写清楚怎么重来。

然后填命令族、链接、安装方式、quick_commands。

### 3. 写事实清单（可以边写镜头边写）

`profile/facts.json` 每条写清：画面上写什么、出现在哪、怎么核。

**先定画面再填清单**：把要讲的三到六件事列出来，每一件对应一条或多条事实。
没有来源的事实不要写——「画面上看着对」不是来源。

### 4. 录素材

```bash
cd mytool-video/project
.venv/bin/python <skill>/scripts/pipeline.py --profile ../profile --project . --record --only record
```

产出 `web/img/<素材>/` 的序列帧和 `meta.json`，以及 `web/img/<素材>-still.png`。

### 5. 抄几何常量

读 `web/img/<素材>/meta.json`：

```jsonc
"cell": {
  "cw": 13.1803,      // 列宽 → 镜头代码的 COLW
  "ch": 30.1871,      // 行高 → CH
  "pad_x": 18.7075,   // 文本左边距 → PADX
  "top": 51.0204      // 第 0 行文字顶端 → TOP
}
```

抄进镜头代码顶部。**不要用「画幅宽 ÷ 列数」估**，理由见 `references/pitfalls.md` 第 2 条。

### 5b. 同步素材清单

`web/project.js` 里的序列帧清单是扫描 `web/img/*/` 得来的快照。重录素材后帧数变了，
这份清单就过期了，页面会按旧帧号去加载已经不存在的图片——渲染一启动就白屏。

```bash
.venv/bin/python tools/timeline.py
```

流水线的 `sync` 步骤做这件事，它排在 `record` 之后、`render` 之前。
这一步会按配音重新对齐时间线，所以配音产物必须在（不在就失败，不会默默改时间线）。

### 6. 写镜头代码

`project/web/shots_<name>.js`。lucid 的镜头约定见 lucid skill 的 `references/engine.md`。

终端卡的标准写法：

```js
const CH = 13.1803 ... // 从 meta.json 抄

function crop(r0, r1, c0, c1) {
  const y0 = r0 === 0 ? 0 : TOP + r0 * CH;
  const y1 = TOP + (r1 + 1) * CH;
  const w = Math.min(PADX + (c1 - c0) * COLW, 1250 - c0 * COLW);
  return { s: [c0 * COLW, y0, w, y1 - y0], c0, r0 };
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
```

`img()` 的 `src` 必须传 4 元数组，不传就没有裁剪。
`CARD` 表和 profile 的 `crop` 要一致。

### 7. 配音与时间线

lucid 的 `tools/tts.py`，`voice.provider` 必须是 `mcode`：

```bash
.venv/bin/python tools/tts.py probe      # 先探能力
.venv/bin/python tools/tts.py             # 合成
```

先合成、测得时长，再排时间线。已有配音和音频结果必须复用，不要重合成。

### 8. 把关

```bash
.venv/bin/python <skill>/scripts/pipeline.py --profile ../profile --project . --only facts,crop
```

- `facts`：每条事实回到来源比对一遍，对不上退出码 1。
- `crop`：裁剪不截字 + profile 与 CARD 表一致 + 几何常量与素材一致。

两条都过才往下走。

### 9. 渲染 + 体检 + 交付

```bash
.venv/bin/python <skill>/scripts/pipeline.py --profile ../profile --project . --final --format all
```

- `render.py --final`：原尺寸、project.json 的帧率、运动模糊、CRF 18，渲完自动体检。
- `deliver.py`：出 `out/交付核对.md`。

体检有硬伤就按报告改，复测。不要改报告了事。

### 10. 嵌回文档站

成片拷到文档站引用的目录，更新 poster 图。
`<video>` 的 src 按页面深度手写（docmd 不改 `<video>` 的 src），
在本地按 Pages 子路径起 http server 实测一遍再部署。

## 改东西时对照哪张表

| 改了什么 | 必须同步改 | 谁来查 |
|---|---|---|
| 画面上的版本号 / URL / 命令列表 | `profile/facts.json` | `facts.py` |
| 工具的输出变了（命令族、参数） | `profile/<name>.json` + 镜头代码的 `L_HELP` 之类的常量 | `facts.py` + `check_crop.py` |
| 某段素材裁几行几列 | profile 的 `crop` **和** 镜头代码的 `CARD` | `check_crop.py` |
| 换了字体 / 列数 / 输出宽度 | 镜头代码的四个几何常量 | `check_crop.py` |
| 重录了素材 | `web/project.js` 的序列帧清单（跑 `tools/timeline.py`） | 渲染一启动就会白屏 |
| 改了镜头时间 | `script/vo.json` 和时间线（用 `tools/timeline.py` 重排） | `render.py` 的体检 |
| 换了配音音色 | `project.json` 的 `voice` | `render.py` 的体检 |

## Windows（win32）等价做法

| 环节 | macOS / Linux | Windows |
|---|---|---|
| 解释器 | `project/.venv/bin/python` | `project\.venv\Scripts\python.exe` |
| 等宽字体 | Menlo / DejaVu Sans Mono | `C:\Windows\Fonts\consola.ttf`（或 `--font` 指定） |
| 构建 | `GOPROXY=... make build` | `$env:GOPROXY="..."; make build` |
| 路径 | 正斜杠 | 正斜杠也行（pathlib 会转） |

换字体等于换网格：Windows 上录出来的素材，`meta.json` 的几何和 macOS 完全不同，
镜头代码的常量要按各自平台的那份 `meta.json` 填，不能互相抄。
