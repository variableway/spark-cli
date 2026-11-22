#!/usr/bin/env python3
"""裁剪自检：素材裁剪范围会不会切掉字、profile 与镜头代码还对不对得上、网格几何准不准。

三个盲区，体检都量不到：

1. **截字**。终端素材是图片，体检只量 textBlock 画的字，看不见图片里的字被卡片边缘切掉。
   一行 72 列的文字裁到 58 列，右边那截就没了——画面上看着像少了个词。
   这里按真实命令输出的行宽逐行核对。

2. **profile 与镜头代码不一致**。profile 里声明每种画幅取哪几行/几列，镜头代码里也有一张
   CARD 表。改了一处忘了另一处，裁剪范围就悄悄变了。这里两边对照。

3. **网格几何对不上**。素材是按「超采样 → 缩到目标宽」渲染的，真实列宽不等于
   「目标宽 ÷ 列数」（文本区两侧还留着内边距）。镜头代码按列定位标注层时若用了名义值，
   标注线会整体偏掉几个百分点。meta.json 里有录制时的真实网格，这里逐个比对。

用法：
  python3 scripts/check_crop.py --profile video/profile
  python3 scripts/check_crop.py --profile video/profile --format 9x16
  python3 scripts/check_crop.py --profile video/profile --skip-geometry
"""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import find_project, load_json, resolve_profile  # noqa: E402

DEFAULT_CARD_ORDER = ['16x9', '1x1', '9x16']
GEOM_TOLERANCE = 0.02   # 像素；小于 1/50 像素的差异是四舍五入，不算错


# ---------- 镜头代码解析 ----------

def strip_js_comments(src):
    """去掉 JS 注释，避免把注释里写的数字当成代码里的常量。

    行注释只在 // 前面是空白或行首时才算注释——这样 https:// 里的 // 不会被吃掉。
    """
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    out = []
    for line in src.split('\n'):
        m = re.search(r'(?<![:\w])//', line)
        out.append(line[:m.start()] if m else line)
    return '\n'.join(out)


def balanced_blocks(text):
    """取出一段文本里顶层的 {...} 块（按出现顺序）。"""
    blocks, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append(text[start:i + 1])
                start = None
    return blocks


def shots_card_table(project, card_order=None):
    """从 web/shots_*.js 里解析出 CARD 表：{画幅: {素材: (末行, 末列)}}。

    CARD 是三元表达式：WIDE ? {...} : SQUARE ? {...} : {...}，
    三个 {...} 按出现顺序对应 card_order 里列的画幅。
    """
    card_order = card_order or DEFAULT_CARD_ORDER
    out = {}
    for f in sorted((project / 'web').glob('shots_*.js')):
        src = strip_js_comments(f.read_text(encoding='utf-8'))
        m = re.search(r'const\s+CARD\s*=', src)
        if not m:
            continue
        rest = src[m.end():]
        end = len(rest)
        depth = 0
        for i, ch in enumerate(rest):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            elif ch == ';' and depth == 0:
                end = i
                break
        blocks = balanced_blocks(rest[:end])
        if len(blocks) != len(card_order):
            print(f'  ⚠️ {f.name} 的 CARD 表有 {len(blocks)} 个分支，'
                  f'与 card_order 的 {len(card_order)} 个画幅对不上，跳过比对')
            continue
        for fmt, row in zip(card_order, blocks):
            vals = re.findall(r'(\w+)\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]', row)
            out.setdefault(fmt, {})
            for name, r1, c1 in vals:
                out[fmt][name] = (int(r1), int(c1))
    return out


def eval_num(expr, env=None):
    """安全地算一个数值表达式（只允许数字、+ - * / 和已知常量）。"""
    env = env or {}

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = walk(node.operand)
            return v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            a, b = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                return a / b
            raise ValueError('不支持的运算')
        if isinstance(node, ast.Name) and node.id in env:
            return float(env[node.id])
        raise ValueError('不支持的表达式')

    try:
        return walk(ast.parse(expr.strip(), mode='eval'))
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError):
        return None


def shots_geometry(project):
    """从 web/shots_*.js 里解析素材几何常量 {CH, TOP, COLW, PADX}。"""
    found = {}
    for f in sorted((project / 'web').glob('shots_*.js')):
        src = strip_js_comments(f.read_text(encoding='utf-8'))
        env = {}
        for name in ('CH', 'TOP', 'COLW', 'PADX'):
            m = re.search(r'\b' + name + r'\s*=\s*([^,;\n]+)', src)
            if not m:
                continue
            v = eval_num(m.group(1), env)
            if v is not None:
                env[name] = v
                found[name] = v
        if found:
            found['__file__'] = f.name
            break
    return found


def asset_meta(project, name):
    """读 web/img/<name>/meta.json（录制器写的）。"""
    p = project / 'web' / 'img' / name / 'meta.json'
    if not p.is_file():
        return None
    try:
        return load_json(p)
    except (ValueError, OSError):
        return None


# ---------- 真实命令输出 ----------

def material_lines(binary, command, prompt):
    """跑命令，返回素材的行（素材第 0 行是提示符行）。"""
    try:
        r = subprocess.run([str(binary)] + [str(c) for c in command],
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout or '') + (r.stderr or '')
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f'执行失败: {e}'
    return [prompt] + out.splitlines(), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default=None, help='profile 文件或目录')
    ap.add_argument('--project', default=None, help='视频工程目录')
    ap.add_argument('--format', default='all', help='画幅，all 或具体名字')
    ap.add_argument('--binary', default=None, help='覆盖 profile 里的二进制路径')
    ap.add_argument('--skip-geometry', action='store_true', help='不查网格几何')
    a = ap.parse_args()

    proj = find_project(a.project)
    profile_file = resolve_profile(a.profile, proj)
    profile = load_json(profile_file)

    card_order = profile.get('card_order') or DEFAULT_CARD_ORDER
    fmts = card_order if a.format == 'all' else [a.format]

    binary = a.binary or (profile.get('binary') or {}).get('path')
    if binary and not Path(str(binary)).exists():
        binary = None
    if not binary:
        print(f'⚠️ 找不到二进制 {(profile.get("binary") or {}).get("path")}，'
              f'裁剪自检跑不了。先构建：{(profile.get("binary") or {}).get("build")}')
        sys.exit(2)

    cards = shots_card_table(proj, card_order)
    problems, checks = [], 0

    # 画幅集合：profile 的 card_order 与 project.json 的 formats 必须一致
    project_json = proj / 'project.json'
    if project_json.is_file():
        declared = set((load_json(project_json).get('formats') or {}).keys())
        if declared and declared != set(card_order):
            problems.append(f'profile.card_order {card_order} 与 project.json 的 formats '
                            f'{sorted(declared)} 不一致')
            print(f'❌ card_order {card_order} 与 project.json formats {sorted(declared)} 不一致')

    for fmt in fmts:
        print(f'== {fmt} ==')
        for name, asset in profile.get('assets', {}).items():
            crop = (asset.get('crop') or {}).get(fmt)
            if not crop:
                print(f'  ⚠️ {name}: profile 里没有 {fmt} 的裁剪范围')
                problems.append(f'{fmt}/{name} profile 缺裁剪范围')
                continue
            r0, r1 = crop['rows']
            c0, c1 = crop['cols']
            checks += 1

            # 1) profile 的裁剪范围 vs 镜头代码里的 CARD 表
            card = (cards.get(fmt) or {}).get(name)
            if card is None:
                print(f'  ⚠️ {name}: 镜头代码里没有 {fmt} 的 CARD 项')
                problems.append(f'{fmt}/{name} 镜头代码 CARD 表缺项')
            elif (card[0], card[1]) != (r1, c1):
                problems.append(
                    f'{fmt}/{name}: profile 裁剪 cols={c1} rows≤{r1}，'
                    f'镜头代码 CARD 表是 cols={card[1]} rows≤{card[0]}')
                print(f'  ❌ {name}: 和镜头代码对不上（profile cols={c1} rows≤{r1} '
                      f'vs CARD cols={card[1]} rows≤{card[0]}）')
            elif (r0, c0) != (0, 0):
                problems.append(f'{fmt}/{name}: profile 裁剪起点是 ({r0},{c0})，'
                                f'镜头代码的 CARD 表表达不了偏移')
                print(f'  ❌ {name}: 裁剪起点非零，CARD 表表达不了')
            else:
                print(f'  ✅ {name}: 与镜头代码一致（rows≤{r1}, cols≤{c1}）')

            # 2) 裁剪范围内有没有超宽的行（会被卡片边缘切掉）
            lines, err = material_lines(binary, asset.get('command', []),
                                        asset.get('prompt', ''))
            if err:
                print(f'  ⚠️ {name}: {err}')
                problems.append(f'{fmt}/{name} {err}')
                continue
            over = []
            for k in range(r0, min(r1 + 1, len(lines))):
                w = len(lines[k].expandtabs(8))
                if w > c1 + 1:
                    over.append((k, w, lines[k]))
            if over:
                for k, w, txt in over:
                    problems.append(f'{fmt}/{name} 第 {k} 行宽 {w} > 裁剪列数 {c1}')
                    print(f'  ❌ {name}: 第 {k} 行宽 {w} > 裁剪列数 {c1}，画面上会被截断：{txt[:60]}')
            else:
                widest = max((len(lines[k].expandtabs(8))
                              for k in range(r0, min(r1 + 1, len(lines)))), default=0)
                print(f'  ✅ {name}: 裁剪 {r0}..{r1} 行 / {c1} 列，最宽一行 {widest} 列')

    # 3) 网格几何：镜头代码常量 vs 录制时写下的真实网格
    if not a.skip_geometry:
        print('\n== 网格几何 ==')
        geom = shots_geometry(proj)
        if not geom:
            print('  ⚠️ 镜头代码里没找到 CH/TOP/COLW/PADX 常量，跳过')
        else:
            mapping = {'CH': 'ch', 'TOP': 'top', 'COLW': 'cw', 'PADX': 'pad_x'}
            for name, asset in profile.get('assets', {}).items():
                meta = asset_meta(proj, name)
                if not meta or 'cell' not in meta:
                    print(f'  ⚠️ {name}: 没有 meta.json 里的网格信息（重录一次素材就有了）')
                    continue
                cell = meta['cell']
                for const, key in mapping.items():
                    if const not in geom or key not in cell:
                        continue
                    want, got = geom[const], cell[key]
                    if abs(want - got) > GEOM_TOLERANCE:
                        problems.append(
                            f'{name}: 镜头代码 {const}={want} 与素材真实 {key}={got} 不符')
                        print(f'  ❌ {name}: {const} 写的是 {want}，素材真实 {key} 是 {got} '
                              f'（差 {abs(want - got):.4f}px）')
                    else:
                        print(f'  ✅ {name}: {const}={want} 与素材一致')

    print(f'\n检查了 {checks} 个裁剪范围')
    if problems:
        print(f'❌ {len(problems)} 处有问题：')
        for p in problems:
            print('   -', p)
        sys.exit(1)
    print('✅ 没有会被截断的行，profile 与镜头代码一致')


if __name__ == '__main__':
    main()
