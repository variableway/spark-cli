# 宿主能力

宿主能力是运行这个 Skill 的环境额外提供的生成或识别能力，例如配音、转写、图像生成、视频生成。不同宿主提供的能力不同，同一个宿主也可能没登录、没联网。

**核心流程不依赖任何宿主能力。** 方案、时间轴、画面、配乐、渲染、体检都只用本机的 Python、Chrome 和 ffmpeg。宿主能力只用来把某一步做得更好或更省事；能力不可用时，按下表的退路继续做，不要停下来，也不要为了用某个能力去改核心工具。

## 现在支持的能力

| 能力 | 后端 | 前提 | 怎么用 | 不可用时 |
|---|---|---|---|---|
| 配音 | `mcode` | 在 MiniMax Code 里运行，`mcode-tools` 在 PATH 上且已登录 | [mcode/voice.md](mcode/voice.md) | auto 换到下一个后端 |
| 配音 | `edge` | 安装了 edge-tts（`python3 -m pip install edge-tts`），能联网 | `voice.provider = "edge"`，见下文 | 请用户提供录音，或做无配音版本 |
| 配音 | `file` | 用户给一段录好或合成好的配音 | `voice.provider = "file"`，见下文 | 不适用 |
| 转写（读音核对） | `mcode` | 同配音的 `mcode` | `tts.py full` 合成后自动转写；单独重跑用 `python3 tools/tts.py asr current` | 跳过自动核对，请用户试听，交付说明里写明 |
| 长命令转到后台后怎么等 | 宿主的命令工具 | 宿主会把超过前台等待时间的命令转到后台 | MiniMax Code 见 [mcode/long-commands.md](mcode/long-commands.md) | 前台一直等到命令结束 |
| 图像生成 | 计划中 | | | |
| 视频生成 | 计划中 | | | |

## 怎么探测

```bash
python3 tools/tts.py probe
```

逐个列出配音后端能不能用、为什么，以及 `auto` 会选哪个。探测 `mcode` 会真的调用一次 `mcode-tools`（只取工具说明，不合成），约十几秒；探测 `edge` 只检查有没有安装。

`voice.provider` 写 `auto`（默认）时，`tts.py full` 依次探测 `mcode`、`edge`，用第一个可用的，并打印选了哪个、其他的为什么不可用。都不可用时它会停下并给出三条路：

1. 安装 edge-tts 后重跑（需要用户同意安装）。
2. 请用户提供录音，改用 `file`。
3. 做无配音版本：`timeline.mode` 改为 `beats` 或 `manual`，用画面文字讲。

## 配音后端的写法

所有后端都读同一份配音稿 `script/vo.json`，都输出 `audio/narration.wav`，之后的 `tools/timeline.py`、字幕、混音完全一样。合成完成后，只要有可用的转写后端，`tts.py full` 就自动转写整段配音，打印和稿子对不上的名字、数字、英文词。加 `--no-asr` 时不自动转写，读音仍要用 `tts.py asr current` 核对。

```json
"voice": {
  "provider": "auto",
  "gap": 1.4,
  "voice_id": "Chinese (Mandarin)_Gentleman", "speed": 1.12,
  "edge": { "voice": "zh-CN-YunxiNeural", "rate": "+0%", "volume": "+0%" },
  "file": { "audio": "audio/recording.wav" }
}
```

- `gap`：镜头之间的停顿（秒），所有合成后端通用。时间轴靠镜头之间 1 秒以上的静音切分镜头，镜头内部的停顿标记要小于 1 秒。
- `voice_id`、`speed`、`emotion`：`mcode` 的参数，见 [mcode/voice.md](mcode/voice.md)。上面的 `voice_id` 只是写法示例：音色按观众和片子的气质选，用 `tts.py voices` 列出、`tts.py audition` 试读比较。
- `edge`：没写音色时用 `zh-CN-YunxiNeural`（自然的年轻男声）；女声可用 `zh-CN-XiaoxiaoNeural`，播音腔男声 `zh-CN-YunyangNeural`，`tts.py voices` 同样列出 edge 的中英文音色。`rate`、`volume` 写成 `"+10%"`、`"-5%"`。整段一次合成；拿到词级边界时在停顿标记处切开并补足停顿，词级时间写进 `audio/narration.words.json`，时间轴直接用它定短句时刻。`(breath)` 这类语气标记 edge-tts 不支持，合成前会去掉。
- `file`：`audio` 是相对工程根目录的路径，任何 ffmpeg 能读的格式都行。录音里镜头之间最好停顿 1 秒以上；停顿不够时，时间轴会按各镜头的字数从较长的停顿里选分界，并列出来请你核对。`tts.py once`（试读）不能用于录音。

## 以后加能力

每种能力放一个说明：它是什么、怎么探测、可用时怎么用、不可用时的退路。宿主专属的用法放在宿主目录下（例如 `mcode/`），探测和选择后端的代码放在用到它的工具里，核心流程只看能力的产物（例如 `audio/narration.wav`），不看它来自哪个后端。
