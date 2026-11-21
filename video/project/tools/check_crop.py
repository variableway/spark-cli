"""裁剪自检：素材裁剪范围里有没有超出列数的行（会在画面上把字截掉）。

自动体检只量 textBlock 画的字，看不见终端素材里的字被卡片边缘切掉，
所以这里按 shots_spark.js 里真正用的裁剪表，核对每一行的宽度。

用法：
  python3 tools/check_crop.py --bin /tmp/spark-new     # 核对全部画幅
  python3 tools/check_crop.py --bin /tmp/spark-new --format 9x16

裁剪表从 web/shots_spark.js 里读（CARD 那几行），改镜头代码后不用同步改这里。
素材的第 0 行是录制器画的提示符行，第 k+1 行才是命令输出的第 k 行。
"""
import sys, re, subprocess, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / 'web' / 'shots_spark.js'

# 素材名 → 跑哪个命令（真实命令，输出才是真的）
CMDS = {
    'help':    ['--help'],
    'version': ['version'],
    'repo':    ['repo', '--help'],
    'skill':   ['skill', '--help'],
}
# 素材第 0 行的提示符（宽度也算进裁剪范围）
PROMPTS = {
    'help': '$ spark --help',
    'version': '$ spark version',
    'repo': '$ spark repo --help',
    'skill': '$ spark skill --help',
}


def crop_table():
    """从 shots_spark.js 里解析出每种画幅的裁剪表：{画幅: {素材: (r1, c1)}}

    CARD 是三元表达式：WIDE ? {...} : SQUARE ? {...} : {...}，
    三个 {...} 按顺序对应 16x9 / 1x1 / 9x16。
    """
    src = SHOTS.read_text(encoding='utf-8')
    blk = re.search(r'const CARD = .*?;', src, re.S)
    if not blk:
        sys.exit('shots_spark.js 里找不到 CARD 表')
    found = re.findall(r'(\{ help: \[[^\]]*\][^}]*\})', blk.group(0))
    if len(found) != 3:
        sys.exit(f'CARD 表里解析出 {len(found)} 个分支（应为 3）：{blk.group(0)}')
    out = {}
    for fmt, row in zip(('16x9', '1x1', '9x16'), found):
        out[fmt] = parse_row(row)
    return out


def parse_row(line):
    m = re.search(r'help: \[(\d+), (\d+)\].*?version: \[(\d+), (\d+)\].*?repo: \[(\d+), (\d+)\].*?skill: \[(\d+), (\d+)\]', line)
    if not m:
        return None
    v = [int(x) for x in m.groups()]
    return {'help': (v[0], v[1]), 'version': (v[2], v[3]), 'repo': (v[4], v[5]), 'skill': (v[6], v[7])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', default='/tmp/spark-new', help='真的 spark 二进制')
    ap.add_argument('--format', default='all')
    a = ap.parse_args()

    binp = Path(a.bin)
    if not binp.exists():
        sys.exit(f'找不到 spark 二进制：{binp}（先 make build，或用 --bin 指定）')

    table = crop_table()
    if not table:
        sys.exit('解析裁剪表失败')

    bad = 0
    for fmt, rows in sorted(table.items()):
        if a.format not in ('all', fmt) or not rows:
            continue
        print(f'== {fmt} ==')
        for name, (r1, c1) in rows.items():
            out = subprocess.run([str(binp)] + CMDS[name], capture_output=True, text=True).stdout.splitlines()
            lines = [PROMPTS[name]] + out          # 素材第 0 行是提示符
            over = []
            for k in range(r1 + 1):                # 裁剪覆盖素材第 0..r1 行
                if k >= len(lines):
                    break
                w = len(lines[k].expandtabs(8))
                if w > c1 + 1:                     # 多留一个字符的余量
                    over.append((k, w, lines[k]))
            if over:
                bad += len(over)
                for k, w, txt in over:
                    print(f'  ❌ {name} 第 {k} 行宽 {w} > 裁剪列数 {c1}，画面上会被截断：{txt[:60]}')
            else:
                widest = max((len(lines[k].expandtabs(8)) for k in range(min(r1 + 1, len(lines)))), default=0)
                print(f'  ✅ {name}：裁剪 0..{r1} 行 / {c1} 列，最宽一行 {widest} 列')
    if bad:
        print(f'\n共 {bad} 处会被截断')
        sys.exit(1)
    print('\n没有会被截断的行')


if __name__ == '__main__':
    main()
