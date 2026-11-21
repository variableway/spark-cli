#!/usr/bin/env python3
"""
终端录制器：真实执行命令，把输出渲染成无损 PNG 帧序列。

给 lucid 的代码视频当素材用——画面内容是**真实命令输出**，但呈现可控：
逐字显现、窗口装饰、颜色高亮都能精确编排，且不经过 GIF 之类的有损中间格式。

设计要点：
  * 内容真实：命令是真的跑一遍，stdout/stderr 原样采集。
  * 节奏合成：真实命令往往几十毫秒就跑完（终端里是瞬间刷完），
    所以时间轴不采自真实耗时，而是脚本按"打字速度 + 逐行打印"合成，
    这样成片里的终端才有节奏感，也完全可控。
  * 无损：直接出 PNG 序列帧，lucid 的 seqFrame() 逐帧取用。

用法：
  python3 tools/record_terminal.py --name spark-help --cmd "/tmp/spark-new --help"

输出：web/img/<name>/0001.png …（lucid 的 seqFrame() 直接取帧）
     web/img/<name>/meta.json（时长 / 帧率 / 画幅等参数）
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = "/System/Library/Fonts/Menlo.ttc"

# 终端配色：与 project.json 的 theme 保持一致
BG = (18, 21, 28)
CHROME = (26, 30, 39)
FG = (215, 222, 233)
DIM = (90, 100, 116)
ACC = (0, 151, 255)
GREEN = (16, 185, 129)
AMBER = (240, 169, 59)
PROMPT = GREEN
CURSOR = (0, 151, 255)


# ---------- 字体与格子 ----------

def load_font(size, index=0):
    return ImageFont.truetype(FONT_PATH, size, index=index)


def cell_metrics(font):
    """等宽字体的字符步进宽度与行高（都用字体真实 advance，不靠 ink bbox 猜）。"""
    cw = int(round(font.getlength("M")))
    ascent, descent = font.getmetrics()
    ch = ascent + descent + int(round(font.size * 0.18))
    return max(cw, 1), max(ch, 1)


# ---------- 输出着色 ----------

def colorize_output(line: str):
    """把一行真实输出切成 (颜色, 文本) 片段。

    规则保持克制：
      * 顶层的小节标题（以冒号结尾）→ 暗色
      * 缩进两格起的子命令名 → 品牌蓝，其余 → 正文灰
      * 其余 → 正文灰
    """
    stripped = line.strip()
    if not stripped:
        return [(FG, "")]

    indent = len(line) - len(line.lstrip())
    if indent == 0 and stripped.endswith(":"):
        return [(DIM, line)]

    if indent >= 2:
        head = len(line) - len(line.lstrip())
        token_end = head
        while token_end < len(line) and not line[token_end].isspace():
            token_end += 1
        runs = []
        if head:
            runs.append((FG, line[:head]))
        runs.append((ACC, line[head:token_end]))
        if token_end < len(line):
            runs.append((FG, line[token_end:]))
        return runs

    return [(FG, line)]


# ---------- 真实执行 ----------

def capture_output(cmd: str, cols: int):
    """真的跑一遍命令，采集原始纯文本输出。"""
    env = {
        **os.environ,
        "TERM": "dumb",
        "NO_COLOR": "1",
        "COLUMNS": str(cols),
        "LINES": "40",
    }
    proc = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        timeout=60,
    )
    text = proc.stdout.decode("utf-8", "replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return lines, proc.returncode


# ---------- 时间轴合成 ----------

def build_schedule(out_lines, cmd_len, cps_cmd, cps_out, line_max, gap):
    """算出时间轴：命令逐字输入 → 停顿 → 输出逐行打印。"""
    type_dur = cmd_len / cps_cmd
    t_out = type_dur + gap

    starts, durs = [], []
    t = t_out
    for line in out_lines:
        d = min(len(line) / cps_out, line_max) if line else 0.03
        starts.append(t)
        durs.append(d)
        t += d
    return type_dur, starts, durs, t


def frame_state(t, cmd_text, out_lines, type_dur, starts, durs, cps_cmd, cps_out):
    """某一时刻屏幕该显示什么。"""
    typed = cmd_text[: max(0, int(min(t, type_dur) * cps_cmd))]

    shown = []
    cursor = (len(typed), None)  # (列, 当前输出行号)
    for i, line in enumerate(out_lines):
        elapsed = t - starts[i]
        if elapsed <= 0:
            break
        if elapsed >= durs[i]:
            shown.append(line)
            cursor = (len(line), i)
            continue
        n = max(1, int(elapsed * cps_out))
        shown.append(line[:n])
        cursor = (n, i)
        break
    return typed, shown, cursor


# ---------- 渲染 ----------

def draw_runs(d, x, y, runs, font, cw):
    """把同色片段整段绘制（等宽字体 advance 精确对齐，比逐字快很多）。"""
    for color, text in runs:
        if not text:
            continue
        d.text((x, y), text, font=font, fill=color)
        x += len(text) * cw
    return x


def render_frame(cmd_text, out_lines, cursor, title, cols, rows, font, cw, ch, pad, chrome_h, show_cursor):
    """把一帧画成 RGB 图像（尺寸固定，不随输出行数变化，避免画面抖动）。"""
    w = cols * cw + pad * 2
    h = chrome_h + (rows + 1) * ch + pad
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)

    # 标题栏
    d.rectangle([0, 0, w, chrome_h], fill=CHROME)
    r = 6
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = pad + 10 + i * 18
        cy = chrome_h // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    tf = ImageFont.truetype(FONT_PATH, int(ch * 0.62), index=0)
    d.text((w // 2, chrome_h // 2), title, font=tf, fill=DIM, anchor="mm")

    # 命令行
    y = chrome_h + pad
    x = pad
    if cmd_text:
        d.text((x, y), "$", font=font, fill=PROMPT)
        x += cw
        d.text((x, y), " ", font=font, fill=DIM)
        x += cw
        d.text((x, y), cmd_text[2:], font=font, fill=FG)
        x += len(cmd_text[2:]) * cw
    if show_cursor and cursor[1] is None:
        d.rectangle([x, y + 3, x + cw - 2, y + ch - 5], fill=CURSOR)
    y += ch

    # 输出
    for i, raw in enumerate(out_lines):
        runs = colorize_output(raw)
        draw_runs(d, pad, y, runs, font, cw)
        if show_cursor and cursor[1] == i:
            end = pad + len(raw) * cw
            d.rectangle([end, y + 3, end + cw - 2, y + ch - 5], fill=CURSOR)
        y += ch

    return img


# ---------- 主流程 ----------

MAXROWS = 26  # 画布固定行数，画面高度不随内容跳动


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--cmd", required=True, help="要执行的命令（真实执行）")
    ap.add_argument("--prompt", default=None, help="画面上显示的命令，默认用 --cmd")
    ap.add_argument("--cols", type=int, default=92)
    ap.add_argument("--rows", type=int, default=MAXROWS)
    ap.add_argument("--fps", type=int, default=20, help="输出帧率")
    ap.add_argument("--scale", type=int, default=2, help="超采样倍数")
    ap.add_argument("--title", default=None)
    ap.add_argument("--head", type=int, default=None, help="只保留前 N 行输出")
    ap.add_argument("--tail", type=int, default=None, help="只保留后 N 行输出")
    ap.add_argument("--skip", type=int, default=0, help="跳过前 N 行输出")
    ap.add_argument("--cps", type=float, default=34.0, help="命令输入速度（字符/秒）")
    ap.add_argument("--out-cps", type=float, default=220.0, help="输出打印速度（字符/秒）")
    ap.add_argument("--line-max", type=float, default=0.34, help="单行最长打印时间（秒）")
    ap.add_argument("--gap", type=float, default=0.32, help="输入完到输出的停顿（秒）")
    ap.add_argument("--hold", type=float, default=1.2, help="结尾停留（秒）")
    ap.add_argument("--out-width", type=int, default=None, help="输出宽度（超采样后缩到这个宽）")
    ap.add_argument("--seq-sec", type=float, default=None, help="只保留前 N 秒作为序列帧（其余丢弃）")
    ap.add_argument("--still", action="store_true", help="把最后一帧另存为静帧 <name>-still.png")
    ap.add_argument("--out", default=None, help="默认 web/img/<name>/")
    args = ap.parse_args()

    title = args.title or args.cmd
    cmd_display = args.prompt if args.prompt is not None else ("$ " + args.cmd)

    print(f"[record] 真实执行：{args.cmd}")
    out_lines, rc = capture_output(args.cmd, args.cols)
    print(f"[record] 采集到 {len(out_lines)} 行输出（exit={rc}）")

    if args.skip:
        out_lines = out_lines[args.skip :]
    if args.head is not None:
        out_lines = out_lines[: args.head]
    if args.tail is not None:
        out_lines = out_lines[-args.tail :]
    if not out_lines:
        out_lines = ["(no output)"]

    font_size = int(26 * args.scale)
    font = load_font(font_size, index=0)
    cw, ch = cell_metrics(font)
    pad = int(22 * args.scale)
    chrome_h = int(38 * args.scale)
    w_size = args.cols * cw + pad * 2
    h_size = chrome_h + (args.rows + 1) * ch + pad

    type_dur, starts, durs, t_end = build_schedule(
        out_lines, len(cmd_display), args.cps, args.out_cps, args.line_max, args.gap
    )
    total = t_end + args.hold
    n_frames = max(int(round(total * args.fps)), 1)

    out_dir = Path(args.out) if args.out else ROOT / "web" / "img" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()

    print(
        f"[record] 时间轴：输入 {type_dur:.2f}s + 输出 {t_end - type_dur - args.gap:.2f}s "
        f"+ 停留 {args.hold:.2f}s = {total:.2f}s → {n_frames} 帧"
    )

    keep_frames = n_frames
    if args.seq_sec is not None:
        keep_frames = max(min(keep_frames, int(round(args.seq_sec * args.fps))), 1)

    last = None
    for i in range(n_frames):
        t = i / args.fps
        typed, shown, cursor = frame_state(
            t, cmd_display, out_lines, type_dur, starts, durs, args.cps, args.out_cps
        )
        show_cursor = (i // 5) % 2 == 0
        frame = render_frame(
            typed, shown, cursor, title, args.cols, args.rows, font, cw, ch, pad, chrome_h,
            show_cursor,
        )
        if args.out_width and args.out_width < frame.width:
            frame = frame.resize(
                (args.out_width, max(1, round(frame.height * args.out_width / frame.width))),
                Image.LANCZOS,
            )
        last = frame
        if i < keep_frames:
            frame.save(out_dir / f"{i + 1:04d}.png")

    if args.still and last is not None:
        still_path = ROOT / "web" / "img" / f"{args.name}-still.png"
        last.save(still_path)
        print(f"[record] 静帧 → {still_path}")

    meta = {
        "name": args.name,
        "cmd": args.cmd,
        "prompt": cmd_display,
        "fps": args.fps,
        "frames": keep_frames,
        "total_frames": n_frames,
        "duration": round(total, 3),
        "size": [last.width, last.height] if last else [w_size, h_size],
        "cols": args.cols,
        "rows": args.rows,
        "type_duration": round(type_dur, 3),
        "lines": len(out_lines),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    print(f"[record] 输出 {keep_frames} 帧 → {out_dir}")
    print(f"[record] 尺寸 {meta['size'][0]}×{meta['size'][1]}")


if __name__ == "__main__":
    main()
