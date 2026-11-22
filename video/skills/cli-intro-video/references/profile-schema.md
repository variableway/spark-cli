# profile 与 facts.json 字段说明

一份 profile 回答两个问题：**这支片讲谁**，以及**画面上每个字怎么来的**。
放在 `profile/<name>.json` 和 `profile/facts.json`。

用 JSON 不用 YAML：工程的 Python 环境里没有 pyyaml，不值得为它加依赖。

## profile/<name>.json

```jsonc
{
  "name": "spark-cli",              // 工具标识，profile 文件名与它一致
  "title": "Spark CLI",             // 显示名
  "summary": "给多仓库工作准备的命令行工具",
  "language": "zh",                 // 画面文字语言

  "binary": {
    "path": "/tmp/spark-new",       // 可执行文件路径；事实核对和录制素材都用它
    "build": "make build",          // 怎么构建（path 没了就按这个重来）
    "build_env": { "GOPROXY": "https://goproxy.cn,direct" },
    "note": "构建产物。/tmp 会被系统清理，没了按 build 重来一遍。"
  },

  "links": {
    "site": "https://variableway.github.io/spark-cli",
    "repo_ssh": "ssh://git@ssh.github.com:443/variableway/spark-cli.git",
    "repo_web": "github.com/variableway/spark-cli"
  },

  "install": "make build  →  ~/.local/bin/spark",   // 画面上的安装说明
  "command_families": ["git", "repo", "hub", ...],   // 命令族，画面上会列
  "quick_commands": [["git", "update"], ...],         // 速查卡上的命令，逐条要能跑通

  "card_order": ["16x9", "1x1", "9x16"],   // 镜头代码 CARD 表的三个分支各对应哪个画幅
  "assets": { ... }
}
```

### card_order

镜头代码里的 `CARD` 是三元表达式：

```js
const CARD = WIDE ? { help: [11, 92], ... }
  : SQUARE ? { help: [5, 58], ... }
  : { help: [10, 58], ... };
```

三个分支按出现顺序对应 `card_order` 里的三个画幅。
**顺序必须对得上**，否则裁剪范围会悄悄串画幅。`check_crop.py` 会拿
`card_order` 和 `project.json` 的 `formats` 键做对照。

### assets.<名字>

每个要录的终端素材一项：

```jsonc
"help": {
  "command": ["--help"],            // 真实执行的参数（前面自动拼 binary.path）
  "prompt": "$ spark --help",       // 画面上显示的那行；和真命令不一致时靠它对齐
  "title": "spark --help",          // 终端窗口标题栏
  "capture": {
    "cols": 92,                     // 终端列数（决定素材宽度和网格）
    "rows": 23,                     // 画布行数（固定，画面不随内容抖动）
    "fps": 15,                      // 序列帧帧率
    "head": 22,                     // 只保留前 N 行输出
    "skip": 1,                      // 跳过前 N 行输出
    "tail": 10,                     // 只保留后 N 行输出
    "out_width": 1250,              // 输出宽度（超采样后缩到这个宽）
    "seq_sec": 12,                  // 序列帧只留前 N 秒
    "seq": false,                   // 只出静帧，不产出序列帧
    "still": true,                  // 另存一张末帧静帧
    "cps": 16                       // 命令逐字输入速度（字符/秒）
  },
  "crop": {                          // 每种画幅裁多少行多少列（闭区间）
    "16x9": { "rows": [0, 11], "cols": [0, 92] },
    "9x16": { "rows": [0, 10], "cols": [0, 58] },
    "1x1":  { "rows": [0, 5],  "cols": [0, 58] }
  }
}
```

`capture` 里没写的参数用录制器的默认值。

`crop` 的**列数必须 ≥ 该范围内最宽的一行**，否则画面上会少字（体检量不到，
只有 `check_crop.py` 管）。`rows` / `cols` 的起点必须是 0——镜头代码的 `CARD` 表
表达不了偏移。

## profile/facts.json

```jsonc
{
  "_note": "画面上出现的每个事实 → 它的来源和校验方式。",
  "_schema": { ... },                 // 可选，给人看的字段说明
  "facts": [
    {
      "id": "version",                // 唯一标识，--only 用它筛
      "on_screen": "v0.4.0 / commit 745cd48 / build 2026-11-15",
      "where": "S03 版本卡",          // 出现在哪个镜头
      "check": { ... }
    }
  ]
}
```

`on_screen` 和 `where` 是给人看的（核对报告会打出来），`check` 是给机器跑的。

### check 的四种类型

**command** — 跑一条命令，输出里必须包含 `expect_all` 的每一串：

```jsonc
"check": {
  "type": "command",
  "command": ["version"],
  "expect_all": ["spark v0.4.0", "commit:     745cd48"]
}
```

- 默认在命令前面拼 `binary.path`。
- `"binary": false` — 这条不是被介绍工具的子命令（比如 `git remote get-url`）。
- `"cwd": "repo"` — 在仓库根目录跑（仓库根从 profile 位置往上找 `.git`）。

**file** — 读仓库里的一个文件，内容必须包含 `expect` 的每一串：

```jsonc
"check": {
  "type": "file",
  "path": "README.md",
  "expect": ["make build", "~/.local/bin/spark"]
}
```

**quick_commands** — `profile.quick_commands` 里的每条子命令逐条跑 `--help`，都得存在：

```jsonc
"check": { "type": "quick_commands", "note": "逐条跑子命令的 --help，确认命令真的存在" }
```

**manual** — 机器核不了，必须人工确认：

```jsonc
"check": {
  "type": "manual",
  "reason": "技能条数随本机环境变，写进片子会变成一条随时会过期的事实，所以故意不写"
}
```

`manual` 不算失败（退出码仍为 0），但会在报告里标出来——
「核不了」和「核过了」是两回事，不能混。

## 退出码

| 脚本 | 0 | 1 | 2 |
|---|---|---|---|
| `facts.py` | 全过（manual 不算失败） | 有事实对不上 | 有事实核不了（缺二进制等） |
| `check_crop.py` | 全过 | 有裁剪/几何问题 | 找不到二进制 |

## 最小示例

`references/example-profile.json` 和 `references/example-facts.json` 是两份可直接用的最小骨架，
`scaffold.py` 生成的 profile 就是照这个形状填的。
