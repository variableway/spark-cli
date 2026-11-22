#!/usr/bin/env python3
"""脚手架：按一个 profile 拉起新的视频工程。

产出（--dest 目录下）：
  profile/<name>.json    工具元数据：二进制、链接、命令族、要录的素材与裁剪范围
  profile/facts.json     画面事实清单：每条写清「画面上写什么」和「怎么核」
  project/               lucid 框架的模板副本（之后只改这个副本，别动框架源码）
  project/web/shots_<name>.js   镜头代码骨架：几何常量占位 + CARD 表 + 一个示例镜头

为什么不复制一个现成工程：现成工程里带着上一个工具的事实、裁剪范围和镜头，
照抄等于把上一条片子里的数字带过来——观众会当真。这里只起骨架，数字都留空。

用法：
  python3 scripts/scaffold.py --dest ../mytool-video --name mytool \\
      --title "My Tool" --binary /usr/local/bin/mytool --build "make build"
"""
import argparse
import glob
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# lucid 框架模板的位置。插件缓存目录名带哈希，所以按 glob 找最新的那个。
TEMPLATE_GLOBS = [
    '~/.minimax/v2/plugin-cache/official/*/skills/lucid/template',
    '~/.minimax/.builtin-skills/lucid/template',
    '~/.minimax/plugins/*/skills/lucid/template',
]


def find_lucid_template(explicit=None):
    """找到 lucid 框架的 template 目录。找不到就报错并说明去哪找。

    优先用同一份 skills/ 目录下的 lucid（项目里 vendored 的副本），
    那样起工程不依赖插件缓存；找不到再往用户目录和插件缓存里找。
    """
    if explicit:
        p = Path(explicit).expanduser()
        if (p / 'project.json').is_file():
            return p.resolve()
        raise SystemExit(f'{p} 里没有 project.json，不是 lucid 模板目录')

    # 用 glob 模块而不是 pathlib：路径中间带 * 的模式 pathlib 不展开
    cands = []
    env = os.environ.get('LUCID_TEMPLATE')
    if env:
        cands.append(Path(env).expanduser())
    # 与本脚本同级的 lucid（skills/lucid/template）
    here = Path(__file__).resolve().parent
    cands.append(here.parent.parent / 'lucid' / 'template')
    for pattern in TEMPLATE_GLOBS:
        cands += [Path(p) for p in glob.glob(os.path.expanduser(pattern))]

    hits = [c for c in cands if (c / 'project.json').is_file()]
    if not hits:
        raise SystemExit(
            '找不到 lucid 框架模板。\n'
            '它的位置在 lucid skill 的目录里（skill 工具加载 lucid 后能看到 Location），\n'
            '或者用 --template / LUCID_TEMPLATE 显式指定。')
    # 多个候选时取最近改动的
    hits.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return hits[0].resolve()


def write_profile(path, name, title, binary, build, assets):
    profile = {
        'name': name,
        'title': title,
        'summary': '（一句话：这个工具是干什么的）',
        'language': 'zh',

        'binary': {
            'path': binary,
            'build': build,
            'note': '构建产物路径。录制素材和事实核对都用它；路径变了要同步改这里。',
        },

        'links': {
            'site': '（官网地址，没有就空着）',
            'repo_ssh': '（仓库 SSH 地址）',
            'repo_web': '（仓库网页地址）',
        },

        'install': '（怎么装，比如 make build → ~/.local/bin/xxx）',

        'command_families': ['（把 --help 里的命令族抄下来）'],
        'quick_commands': [['（一条常用子命令）']],

        'card_order': ['16x9', '1x1', '9x16'],

        'assets': assets,
    }
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    return profile


def write_facts(path, name):
    doc = {
        '_note': '画面上出现的每个事实 → 它的来源和校验方式。'
                 'facts.py 真跑一遍比对，编造的事实渲染前就被拦住。',
        '_schema': {
            'on_screen': '画面上出现的内容（给人和体检报告看）',
            'where': '出现在哪个镜头',
            'check': {
                'command': '跑这个命令，输出里必须包含 expect_all 里的每一串；'
                           'binary:false 表示不是被介绍工具的子命令；cwd:"repo" 表示在仓库根跑',
                'file': '读这个文件（相对仓库根），内容里必须包含 expect 里的每一串',
                'quick_commands': 'profile.quick_commands 里的每条子命令都得存在',
                'manual': '机器核不了，必须人工确认；reason 里写清为什么核不了',
            },
        },
        'facts': [
            {
                'id': 'version',
                'on_screen': '（画面上写的版本号、提交、构建时间）',
                'where': 'S0x 版本卡',
                'check': {
                    'type': 'command',
                    'command': ['version'],
                    'expect_all': ['（从真实输出里抄一串）'],
                },
            },
            {
                'id': 'example',
                'on_screen': '（画面上写的一句话）',
                'where': 'S0x',
                'check': {
                    'type': 'manual',
                    'reason': '（为什么机器核不了）',
                },
            },
        ],
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
    return doc


SHOTS_TEMPLATE = """/* =========================================================
   shots_{name}.js —— {title} 介绍片（镜头代码骨架）

   约定：SHOT.<id> = function (ctx, t, S) {{}}，画面只由 t 算出；EV() 写在文件顶层。

   素材几何：先按 profile 录一遍素材，再把下面四个常量改成
   web/img/<素材名>/meta.json 里 cell 字段的真实值（check_crop.py 会逐个比对，
   对不上就拦下来）。别用「画幅宽 ÷ 列数」估，那是名义值，会偏几个百分点。

   CARD 表：每个画幅取素材的哪几行/几列，{last_row} 行以内、{last_col} 列以内。
   这张表必须和 profile 里 assets.<名字>.crop 完全一致（check_crop.py 双向对照）。
   ========================================================= */
'use strict';
(function () {{

  // TODO 录完素材后按 meta.json 的 cell 改这四个数
  const CH = 0, TOP = 0, COLW = 0, PADX = 0;
  const B = safeBox();
  const WIDE = !PORTRAIT && !SQUARE;
  const HEAD_H = (WIDE ? 190 : PORTRAIT ? 380 : 235) * U;

  const CARD = WIDE
    ? {{ {card_wide} }}
    : SQUARE
      ? {{ {card_square} }}
      : {{ {card_portrait} }};

  // 裁一段素材：行区间（闭）+ 列区间（闭）
  function crop(r0, r1, c0, c1) {{
    const y0 = r0 === 0 ? 0 : TOP + r0 * CH;
    const y1 = TOP + (r1 + 1) * CH;
    const w = Math.min(PADX + (c1 - c0) * COLW, {img_width} - c0 * COLW);
    return {{ s: [c0 * COLW, y0, w, y1 - y0], c0, r0 }};
  }}
  // 按来源尺寸等比放进区域
  function fitBox(box, cw, ch, align) {{
    const s = Math.min(box.w / cw, box.h / ch);
    const w = cw * s, h = ch * s, a = align || '';
    const x = /left/.test(a) ? box.x : /right/.test(a) ? box.x + box.w - w : box.x + (box.w - w) / 2;
    const y = /top/.test(a) ? box.y : /bottom/.test(a) ? box.y + box.h - h : box.y + (box.h - h) / 2;
    return {{ x, y, w, h, s }};
  }}
  // 素材里某一行（从第 c 列起 n 个字符）在画面上的矩形
  function rowAt(d, c, k, n, c0) {{
    const s = d.w / c.s[2], cc = c0 ?? c.c0;
    return {{
      x: d.x + (PADX + (cc - c.c0) * COLW) * s,
      y: d.y + (TOP + k * CH - c.s[1]) * s,
      w: n * COLW * s,
      h: CH * s,
    }};
  }}

  // ---------------------------------------------------------------- S01 示例镜头
  SHOT.S01 = function (ctx, t, S) {{
    screen(ctx);
    const HEAD = {{ x: B.x, y: B.y, w: B.w, h: HEAD_H }};
    const AREA = {{ x: B.x, y: B.y + HEAD_H + 26 * U, w: B.w, h: B.h - HEAD_H - 26 * U }};

    const c = crop(0, CARD.{first_asset}[0], 0, CARD.{first_asset}[1]);
    const d = fitBox(AREA, c.s[2], c.s[3], 'top');
    img(ctx, seqFrame('{first_asset}', t - S.t0, 15), d.x, d.y, d.w, d.h, {{ fit: 'fill', src: c.s, r: 14 * U }});

    const [h1, h2] = split(HEAD, 'col', [1, 1], 8 * U);
    textBlock(ctx, '（一句话钩子）', h1, {{ role: 'title', valign: 'bottom', t, color: COL.ink, max: 88 * U }});
    textBlock(ctx, '（副标题）', h2, {{ role: 'title', valign: 'top', t, color: COL.acc, max: 88 * U }});
  }};

}})();
"""


def write_shots(path, name, title, assets, card_order, img_width=1250):
    """写镜头代码骨架：CARD 表按 profile 的裁剪范围填，几何留占位。"""
    by_fmt = {fmt: {} for fmt in card_order}
    for a_name, asset in assets.items():
        crop = asset.get('crop', {})
        for fmt in card_order:
            c = crop.get(fmt)
            if c:
                by_fmt[fmt][a_name] = (c['rows'][1], c['cols'][1])

    def render(fmt):
        items = by_fmt.get(fmt) or {}
        if not items:
            return ''
        return ', '.join(f'{k}: [{v[0]}, {v[1]}]' for k, v in items.items())

    first = next(iter(assets), 'help')
    last_row = max((v[0] for fmt in card_order for v in by_fmt.get(fmt, {}).values()),
                   default=0)
    last_col = max((v[1] for fmt in card_order for v in by_fmt.get(fmt, {}).values()),
                   default=0)

    text = SHOTS_TEMPLATE.format(
        name=name, title=title, card_wide=render(card_order[0]),
        card_square=render(card_order[1]), card_portrait=render(card_order[2]),
        first_asset=first, last_row=last_row, last_col=last_col,
        img_width=img_width,
    )
    path.write_text(text, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True, help='新工程放在哪')
    ap.add_argument('--name', required=True, help='工具名（kebab-case，用作 profile 文件名）')
    ap.add_argument('--title', default=None, help='显示名，默认用 name')
    ap.add_argument('--binary', default=None, help='被介绍工具的可执行文件路径')
    ap.add_argument('--build', default=None, help='构建命令')
    ap.add_argument('--template', default=None, help='lucid 模板目录，默认自动找')
    ap.add_argument('--force', action='store_true', help='目标已存在时也继续')
    a = ap.parse_args()

    dest = Path(a.dest).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()) and not a.force:
        raise SystemExit(f'{dest} 已存在且非空。加 --force 覆盖，或换个目录。')

    template = find_lucid_template(a.template)
    print(f'[scaffold] lucid 模板：{template}')

    prof_dir = dest / 'profile'
    proj_dir = dest / 'project'
    prof_dir.mkdir(parents=True, exist_ok=True)

    if not proj_dir.exists():
        shutil.copytree(template, proj_dir)
        # 模板自带的示例工程文件不要留着
        for junk in ('examples',):
            j = proj_dir / junk
            if j.exists():
                shutil.rmtree(j)
        print(f'[scaffold] 框架模板 → {proj_dir}')
    else:
        print(f'[scaffold] {proj_dir} 已存在，跳过模板复制')

    title = a.title or a.name
    assets = {
        'help': {
            'command': ['--help'],
            'prompt': f'$ {a.name} --help',
            'title': f'{a.name} --help',
            'capture': {'cols': 92, 'rows': 23, 'fps': 15, 'head': 22,
                        'out_width': 1250, 'seq_sec': 12, 'still': True, 'cps': 16},
            'crop': {
                '16x9': {'rows': [0, 11], 'cols': [0, 92]},
                '9x16': {'rows': [0, 10], 'cols': [0, 58]},
                '1x1': {'rows': [0, 5], 'cols': [0, 58]},
            },
        },
    }
    write_profile(prof_dir / f'{a.name}.json', a.name, title,
                  a.binary or f'/path/to/{a.name}', a.build or '（构建命令）', assets)
    write_facts(prof_dir / 'facts.json', a.name)
    write_shots(proj_dir / 'web' / f'shots_{a.name}.js', a.name, title, assets,
                ['16x9', '1x1', '9x16'])

    print(f'[scaffold] profile → {prof_dir}')
    print(f'[scaffold] 镜头骨架 → {proj_dir / "web" / f"shots_{a.name}.js"}')
    print('\n下一步：')
    print(f'  1. 按 profile 录素材：'
          f'python3 <skill>/scripts/pipeline.py --profile {prof_dir} --record --only record')
    print(f'  2. 把 shots 里的 CH/TOP/COLW/PADX 改成 meta.json 的真实值')
    print(f'  3. 填 facts.json，然后跑 check_crop 与 facts 把关')


if __name__ == '__main__':
    main()
