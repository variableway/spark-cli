---
title: Intro Video
description: The spark-cli intro video in three aspect ratios — embed it or download it
---

# Intro Video

52 seconds on what spark-cli actually does.

Everything on screen is real: the terminal runs a real `spark --help`, the version and
commit come from a real `spark version`, and the ten command families in the diagram are
exactly the commands in `Available Commands` besides `help`. Subtitles are burned in
(Chinese + English).

| Ratio | Where it goes | File |
|-------|---------------|------|
| 16:9 | Docs site, README | [spark-cli-16x9.mp4](/assets/video/spark-cli-16x9.mp4) |
| 9:16 | Social / vertical | [spark-cli-9x16.mp4](/assets/video/spark-cli-9x16.mp4) |
| 1:1 | Site hero | [spark-cli-1x1.mp4](/assets/video/spark-cli-1x1.mp4) |

## 16:9 — docs site and README

<video src="../../assets/video/spark-cli-16x9.mp4" width="100%" controls preload="metadata" poster="../../assets/video/spark-cli-16x9.jpg"></video>

## 9:16 — social / vertical

<video src="../../assets/video/spark-cli-9x16.mp4" width="360" controls preload="metadata" poster="../../assets/video/spark-cli-9x16.jpg"></video>

## 1:1 — site hero

<video src="../../assets/video/spark-cli-1x1.mp4" width="480" controls preload="metadata" poster="../../assets/video/spark-cli-1x1.jpg"></video>

## Re-rendering it

The project lives in [`video/project`](https://github.com/variableway/spark-cli/tree/main/video/project):

```bash
cd video/project
./.venv/bin/python tools/render.py --final --format all
```

The footage is recorded from live commands — the terminal capture runs the real
`spark --help` and `spark version`, and `tools/check_crop.py` checks every crop against
the real output width so no line gets cut off at the card edge.
