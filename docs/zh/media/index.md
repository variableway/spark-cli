---
title: 介绍片
description: spark-cli 介绍片的三种画幅，可直接嵌入或下载
---

# 介绍片

52 秒，把 spark-cli 是干什么的讲清楚。

画面里的东西都是真的：终端里敲的是真的 `spark --help`，版本号和 commit 来自真的
`spark version`，架构图上那十个命令族就是 `Available Commands` 里除 `help` 之外的全部命令。
中英双语字幕烧在画面里。

| 画幅 | 用在哪 | 文件 |
|------|--------|------|
| 16:9 | 文档站、README | [spark-cli-16x9.mp4](/assets/video/spark-cli-16x9.mp4) |
| 9:16 | 社媒竖版 | [spark-cli-9x16.mp4](/assets/video/spark-cli-9x16.mp4) |
| 1:1 | 官网首屏 | [spark-cli-1x1.mp4](/assets/video/spark-cli-1x1.mp4) |

## 16:9 — 文档站与 README

<video src="../assets/video/spark-cli-16x9.mp4" width="100%" controls preload="metadata" poster="../assets/video/spark-cli-16x9.jpg"></video>

## 9:16 — 社媒竖版

<video src="../assets/video/spark-cli-9x16.mp4" width="360" controls preload="metadata" poster="../assets/video/spark-cli-9x16.jpg"></video>

## 1:1 — 官网首屏

<video src="../assets/video/spark-cli-1x1.mp4" width="480" controls preload="metadata" poster="../assets/video/spark-cli-1x1.jpg"></video>

## 怎么重做这支片

工程在 [`video/project`](https://github.com/variableway/spark-cli/tree/main/video/project)，
一条命令重出：

```bash
cd video/project
./.venv/bin/python tools/render.py --final --format all
```

素材是现跑的：终端录制跑的是真的 `spark --help` 和 `spark version`，
`tools/check_crop.py` 按真实输出的行宽核对裁剪范围，防止字被卡片截断。
