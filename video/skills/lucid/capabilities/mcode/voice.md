# MiniMax Code：配音与转写

在 MiniMax Code 里，`tools/tts.py` 通过 `mcode-tools` 调用 MiniMax 的语音合成和音频理解。`voice.provider` 写 `auto`（默认）或 `mcode` 时使用。

## 前提与探测

- `mcode-tools` 在 PATH 上，并且已登录。`python3 tools/tts.py probe` 会调用一次 `mcode-tools connector tool connector__matrix__synthesize_speech` 确认。
- 在别的宿主里运行时 `mcode-tools` 可能存在但不能用，例如报 `Embedded mcode-tools requires MCODE_AUTH_PROVIDER=shared-broker`。这类登录错误不要重试：保持 `auto` 让它换到下一个后端，或改用 `edge`、`file`（见 [../README.md](../README.md)）。

## 合成

```bash
python3 tools/tts.py full v1     # 整段一次合成 → audio/narration_v1.mp3/.wav，并复制为 audio/narration.mp3/.wav；合成后自动转写核对
python3 tools/timeline.py        # 按配音出时间轴
```

整段一次合成，镜头之间用 `<#gap#>` 停顿标记连接。一句一句分开合成，语气和音量会不连贯。合成加转写通常要一两分钟以上，在 MiniMax Code 里常会转到后台，等法见 [long-commands.md](long-commands.md)。

- **音色。** 中文片默认 `Chinese (Mandarin)_Gentleman`（温润男声），英文片默认 `English_Trustworthy_Man`；`voice.voice_id` 没写时，`tts.py` 按 `vo.json` 的 `lang` 选其中一个并打印一行提示。`speed` 常用 1.12。只在另一个声音明显更合适时才换（儿童片、用户点名了语气或性别）；用户指定了音色就用他的。
  - 换音色时：`python3 tools/tts.py voices [--lang zh|en] [--grep 关键词]` 列出可用的 `voice_id`、性别和年龄感、一句描述；`python3 tools/tts.py audition "<片中的一句话>" <voice_id> <voice_id> [--speed 1.1]` 用同一句话分别合成到 `audio/audition/`，打印每个的时长和转写。选定后写进 `project.json` 的 `voice.voice_id`，`voice.why` 写一句为什么换（`deliver.py` 抄进交付核对）。
- **语气。** 默认不传 `emotion`，让模型自己判断语气。传 `happy` 会多出怪异的哼声。
- **语气标记。** `(breath)` 吸气声、`(chuckle)` 轻笑可以写进配音稿。
- **停顿标记。** `<#0.3#>` 是 0.3 秒停顿。镜头内部的停顿标记必须小于 1 秒，否则会被当成镜头分界；镜头之间的停顿由 `voice.gap` 决定（默认 1.4 秒）。
- **试读。** `python3 tools/tts.py once args.json out.mp3 [--asr]`，`args.json` 写 `{"text": "...", "voice_id": "...", "speed": 1.12}`，用来比较一个词的几种写法。

## 转写与读音核对

`tts.py full` 合成完就自动转写：按镜头间隙把整段配音切成约 2 分钟一段，逐段转写到 `audio/asr/`，并打印和稿子对不上的名字、数字、英文词。加 `--no-asr` 时不自动转写，之后仍要用 `python3 tools/tts.py asr current` 转写核对。

**核对读音靠转写。** 你听不到声音。通读转写和打印出的差异，重点看英文名、多音字、数字。读错时按顺序处理：

1. 用 `tts.py once` 短句试读几种写法。短句读对不代表整段读对，改完看整段的转写。
2. 改成中文指代。
3. 在 `vo.json` 的 `tts_fix` 里换同音字（只影响合成，画面文字不变）。

改完重新合成，它会自动再转写一遍。四项并列的句子读起来像念 PPT，改成有主次的口语句；单字问句容易读错声调，把问句写长。

用 `edge` 或 `file` 配音时，只要 `mcode` 可用，`asr` 仍然用它转写。

## 常见错误

| 现象 | 处理 |
|---|---|
| 服务偶发 500、429、`temporarily unavailable`、服务器繁忙 | 脚本每 20 秒自动重试，最多 15 次。不要拆分长文本 |
| `MCODE_AUTH_PROVIDER`、未登录 | 不在 MiniMax Code 里或没登录，脚本直接停下。改用 `auto`、`edge` 或 `file` |
| 时间轴提示「>=1 秒的静音有 N 处，应为 M 处」并列出它选的镜头分界 | 镜头内部有大于等于 1 秒的停顿标记，或合成时漏掉了镜头间的停顿。分界选对了可以继续；选错了就把镜头内停顿改小，重新合成 |
| 转写不出开头的气声 | `(breath)`、「嘘」这类气声转写不出字属正常 |
