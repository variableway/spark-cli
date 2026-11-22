#!/usr/bin/env python3
"""生成 video/docs/architecture.html —— 视频工作流的架构图与模块图。

为什么用生成器而不是手写 HTML：图里的每个文件数、帧数、差异清单都必须来自
真实的文件系统，不能是「写的时候大概是这个数」。脚本扫一遍工程，把结果填进
页面；工程改了重跑一次，页面就跟着变。

口径（写在页面上，也在这里实现）：
  * 文件清单：以 `git ls-files video` 为准——入库文件。工程内生成的产物
    （out/ 成片、web/img/ 帧序列、.venv、__pycache__）不在清单里。
  * 交叉复核：另外用 find 独立数一遍代码文件，结果必须一致，不一致就报错退出。
  * 本页不统计代码行数——行数不是这套工作流的事实，写进去只会变成需要维护的
    噪音。文件个数、帧数、字节数才是会随工程变化的真实刻度。

用法：
  python3 video/docs/build_architecture.py
  python3 video/docs/build_architecture.py --check   # 只校验，不写文件
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DOCS = Path(__file__).resolve().parent
VIDEO = DOCS.parent
REPO = VIDEO.parent
OUT = DOCS / 'architecture.html'

TEXT_EXT = {'.py', '.js', '.html', '.json', '.md', '.txt', '.css', '.yml', '.yaml', '.sh'}
CODE_EXT = {'.py', '.js'}
DOC_EXT = {'.md'}
BIN_EXT = {'.woff2', '.woff', '.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4', '.wav', '.svg', '.ico', '.pdf'}

MAX_INLINE = 16 * 1024      # 超过这个字节数只内嵌前 HEAD_LINES 行
HEAD_LINES = 100

ACCENT = '#a8431f'
INK = '#1d1b18'
INK2 = '#6d6862'
RULE = '#e3ded4'
PANEL = '#fffdf9'
CHIP_BG = '#f0ece4'
CHIP_DIM_BG = '#f6f4ef'


# ---------------------------------------------------------------- 小工具

def esc(t) -> str:
    return html.escape(str(t), quote=True)


def git(*args: str) -> str:
    r = subprocess.run(['git', *args], cwd=str(REPO), capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'git {args} 失败：{r.stderr.strip()}')
    return r.stdout.strip()


def fmt_int(n: int) -> str:
    return f'{n:,}'


def kb(n: int) -> str:
    if n < 1024:
        return f'{n} B'
    if n < 1024 * 1024:
        return f'{n / 1024:.1f} KB'
    return f'{n / 1048576:.2f} MB'


def vw(text: str, size: float) -> float:
    """估算 SVG 文本宽度：CJK 与全角标点按 1em，其余按 0.58em。

    字号调大后按「字符个数 × 固定系数」估宽会算少——中文标签会被撑出边框。
    """
    w = 0.0
    for ch in text:
        w += size if ord(ch) > 0x2E7F else size * 0.58
    return w


CHIP_FS = 12.5          # 图 1 的文件小标签字号


def chip_w(text: str) -> float:
    """一个小标签的宽度：左右各留一点内边距。"""
    return 16 + vw(text, CHIP_FS) + 8


# ---------------------------------------------------------------- 扫描

class Scan:
    """工程文件清单与统计。"""

    SELF = 'docs/architecture.html'          # 本页自己：计入文件数，但不参与统计与内嵌

    def __init__(self):
        self.tracked: list[str] = []          # 相对 video/ 的入库文件路径
        self.bytes: dict[str, int] = {}       # 路径 -> 字节数
        self.text: dict[str, bool] = {}       # 路径 -> 是否文本
        self._load()

    def _load(self):
        out = git('ls-files', 'video')
        for raw in out.splitlines():
            if not raw:
                continue
            rel = raw[len('video/'):] if raw.startswith('video/') else raw
            self.tracked.append(rel)
        for rel in self.tracked:
            p = VIDEO / rel
            ext = p.suffix.lower()
            self.text[rel] = ext in TEXT_EXT or p.name == '.gitignore'
            self.bytes[rel] = p.stat().st_size if p.exists() else 0

    # -- 统计口径 ---------------------------------------------------
    def code_files(self) -> list[str]:
        """流水线代码：.py / .js，排除 docs/（本页生成脚本本身）。"""
        return [r for r in self.tracked
                if Path(r).suffix.lower() in CODE_EXT and self.text[r]
                and not r.startswith('docs/')]

    def doc_files(self) -> list[str]:
        return [r for r in self.tracked
                if Path(r).suffix.lower() in DOC_EXT and self.text[r]
                and r != self.SELF]

    def text_files(self) -> list[str]:
        return [r for r in self.tracked if self.text[r] and r != self.SELF]

    def binary_files(self) -> list[str]:
        return [r for r in self.tracked if not self.text[r]]

    def cross_check(self) -> int:
        """独立复核：用 find 再数一遍 .py/.js 的文件个数。

        不用行数——行数不进页面，也不值得维护。只复核文件个数，
        结果必须与 git ls-files 的口径一致，不一致就报错退出。
        """
        find_cmd = ("find . -type f \\( -name '*.py' -o -name '*.js' \\) "
                    "-not -path '*/__pycache__/*' -not -path '*/.venv/*' "
                    "-not -path '*/out/*' -not -path '*/frames/*' "
                    "-not -path '*/references/*' -not -path '*/node_modules/*' "
                    "-not -path './docs/*'")
        r = subprocess.run(f'{find_cmd} | wc -l', cwd=str(VIDEO),
                           shell=True, capture_output=True, text=True)
        try:
            return int(r.stdout.strip())
        except ValueError:
            return -1


# ---------------------------------------------------------------- 模块定义

# layer, name, paths, role —— 文件数与行数由扫描结果算，不手写
MODULES = [
    ('配置层', '工具档案', ['profile/spark-cli.json'],
     '这支片讲谁：二进制与构建命令、命令族、要录的素材、每种画幅的裁剪范围。声明的真相。'),
    ('配置层', '事实清单', ['profile/facts.json'],
     '画面上出现的每一个事实，以及一条可执行的核对方式。渲染前逐条比对。'),
    ('工作流层', '工作流脚本', ['skills/cli-intro-video/scripts'],
     '录素材、事实核对、裁剪自检、流水线、脚手架——「内容必须真实」的落脚处。'),
    ('工作流层', '工作流说明', ['skills/cli-intro-video/SKILL.md', 'skills/cli-intro-video/references'],
     '什么时候用这套流程、profile 每个字段怎么写、踩过的坑。'),
    ('工作流层', '演进计划', ['docs/cli-video-skill-plan.md'],
     '这套流程要变成能长期用的 Skill 还差什么：素材层怎么生成的、改文案为什么难、'
     '引擎层有没有硬编码、下一步先做哪一步。'),
    ('工作流层', '改片手册', ['docs/film-refresh-playbook.md'],
     'CLI 变了以后怎么把片子跟上：六环的顺序、每环改什么怎么验、实测踩过的六个坑。'),
    ('工作流层', '改片手册二', ['docs/film-refresh-io.md'],
     '输入输出结构与手动流程：每个文件谁产出谁消费、改完按哪条路径重跑、'
     '配音怎么生成、多音字错了怎么办、S01 这些编号是什么。'),
    ('素材层', '终端素材', ['project/web/img'],
     '命令真跑一遍录下的无损 PNG 帧序列；静帧入库，帧序列不入库。'),
    ('镜头层', '镜头与引擎', ['project/web'],
     '自写镜头 shots_spark.js（六个镜头）＋ lucid 画布引擎 core.js / main.js。'),
    ('引擎层', '框架工具', ['skills/lucid/template/tools'],
     '渲染、体检、交付核对、时间线、配音——lucid 引擎的全部命令行。'),
    ('引擎层', '框架音频', ['skills/lucid/template/audio'],
     '配乐合成、鼓点检测、音色库。'),
    ('引擎层', '框架引擎', ['skills/lucid/template/web', 'skills/lucid/template/project.json',
                          'skills/lucid/template/script', 'skills/lucid/template/requirements.txt',
                          'skills/lucid/template/.gitignore'],
     '画布引擎的 JS 源码与模板工程配置。'),
    ('引擎层', '框架示例', ['skills/lucid/template/examples', 'project/examples'],
     'explainer_voice 与 promo_beats 两个片型的示例工程。'),
    ('引擎层', '框架说明', ['skills/lucid/references', 'skills/lucid/capabilities',
                          'skills/lucid/SKILL.md', 'skills/lucid/PROVENANCE.md'],
     '引擎接口、素材、配音、工艺、片型指南、宿主能力与来源授权说明。'),
    ('工作副本', '框架副本', ['project/tools', 'project/audio'],
     'lucid 框架的工作副本，与 template/ 逐字节相同；框架升级时整体覆盖即可。'),
    ('工作副本', '项目数据', ['project/project.json', 'project/script', 'project/timeline.json',
                          'project/assets'],
     '片型、画幅、主题、配音稿、逐句英译、时间线、品牌素材。'),
    ('产物层', '成片与交付', ['docs/assets/video'],
     '三画幅成片与海报，供文档站嵌入；工程内的 out/ 另存交付核对表（不入库）。'),
]

# 素材清单的唯一真源是 profile/spark-cli.json 的 assets 字段。
# 生成器不写死素材名——CLI 重构删掉一个素材，页面跟着变，
# 不会在表里留下 0 帧、0×0 的僵尸行（2026-11-22 那次就漏了 repo/skill）。
def profile_assets() -> dict:
    try:
        pj = json.loads((VIDEO / 'profile' / 'spark-cli.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return pj.get('assets') or {}


ASSETS = profile_assets()
ASSET_NAMES = list(ASSETS)


# 图 1 的层。目录规模全部由扫描结果算，不手写。
# chip = (显示名, 文件路径, 模式)  模式：'name' 只显示文件名，'frames' 追加帧数，'fixed' 原样显示
LAYERS = [
    ('①', '配置层', 'profile/', [
        ('spark-cli.json', 'profile/spark-cli.json', 'name'),
        ('facts.json', 'profile/facts.json', 'name'),
    ]),
    ('②', '工作流层', 'skills/cli-intro-video/scripts/', [
        ('pipeline.py', 'skills/cli-intro-video/scripts/pipeline.py', 'name'),
        ('facts.py', 'skills/cli-intro-video/scripts/facts.py', 'name'),
        ('check_crop.py', 'skills/cli-intro-video/scripts/check_crop.py', 'name'),
        ('record_terminal.py', 'skills/cli-intro-video/scripts/record_terminal.py', 'name'),
        ('check_pron.py', 'skills/cli-intro-video/scripts/check_pron.py', 'name'),
        ('refresh.py', 'skills/cli-intro-video/scripts/refresh.py', 'name'),
        ('scaffold.py', 'skills/cli-intro-video/scripts/scaffold.py', 'name'),
        ('_paths.py', 'skills/cli-intro-video/scripts/_paths.py', 'name'),
    ]),
    ('③', '素材层', 'project/web/img/', [
        (f'{n}/', f'project/web/img/{n}/meta.json', 'frames') for n in ASSET_NAMES
    ]),
    ('④', '镜头层', 'project/web/', [
        ('shots_spark.js（自写）', 'project/web/shots_spark.js', 'name'),
        ('core.js', 'project/web/core.js', 'name'),
        ('main.js', 'project/web/main.js', 'name'),
        ('index.html', 'project/web/index.html', 'name'),
        ('modules/editorial.js', 'project/web/modules/editorial.js', 'name'),
        ('bg.js', 'project/web/bg.js', 'name'),
        ('gl3d.js', 'project/web/gl3d.js', 'name'),
    ]),
    ('⑤', '引擎层', 'skills/lucid/template/tools/', [
        ('render.py', 'skills/lucid/template/tools/render.py', 'name'),
        ('checkup.py', 'skills/lucid/template/tools/checkup.py', 'name'),
        ('deliver.py', 'skills/lucid/template/tools/deliver.py', 'name'),
        ('timeline.py', 'skills/lucid/template/tools/timeline.py', 'name'),
        ('tts.py', 'skills/lucid/template/tools/tts.py', 'name'),
        ('layout.py', 'skills/lucid/template/tools/layout.py', 'name'),
        ('assets.py', 'skills/lucid/template/tools/assets.py', 'name'),
        ('common.py', 'skills/lucid/template/tools/common.py', 'name'),
    ]),
    ('⑥', '产物层', 'project/out/ ＋ docs/assets/video/', [
        ('project/out/*.mp4  16x9 / 9x16 / 1x1', '', 'fixed'),
        ('project/out/交付核对.md', '', 'fixed'),
        ('docs/assets/video/  3 个 mp4 ＋ 3 张海报', '', 'fixed'),
    ]),
]

FLOW = [
    '声明的真相：profile 写什么，画面就得是什么',
    'record_terminal.py 真跑一遍命令，录成无损帧序列',
    'seqFrame() 取帧，meta.json 给出真实网格',
    'render.py 打开 Chrome 逐帧渲染',
    'ffmpeg 合成 MP4，自动体检与交付核对',
]

# 步骤名、脚本、输入、输出、闸门、一句话
PIPELINE = [
    ('facts', 'facts.py', 'facts.json', '核对结论', '退出码≠0 即停', '比对画面事实的来源'),
    ('crop', 'check_crop.py', '素材＋profile', '裁剪与几何结论', '退出码≠0 即停', '裁剪不截字、几何对得上'),
    ('record', 'record_terminal.py', 'capture 参数', 'PNG 帧＋meta.json', '退出码≠0 即停', '真跑命令，录成帧序列'),
    ('sync', 'timeline.py', '配音＋帧目录', 'timeline.json', '退出码≠0 即停', '刷新时间线与帧清单'),
    ('render', 'render.py', '工程＋时间线', 'MP4＋体检报告', '体检有硬伤', '逐帧渲染并自动体检'),
    ('deliver', 'deliver.py', 'out/ 成片', '交付核对.md', '只报告不拦', '把成片事实填进交付表'),
]


DIFF_FILES = [
    ('project/project.json', '手写', '片型、画幅、主题、章节、素材清单——原件是空白模板'),
    ('project/script/vo.json', '手写', '配音稿与逐句英译'),
    ('project/web/index.html', '工具生成',
     'timeline.py 按 shots_spark.js 的存在自动补上的一行 script 标签'),
    ('project/web/shots_spark.js', '手写', '六个镜头的镜头代码，原件里没有这个文件'),
    ('project/web/project.js、web/timeline.js、timeline.json', '工具生成',
     'timeline.py 的产物：画面配置与时间线快照'),
    ('project/web/img/**、project/audio/**、project/assets/**', '工具生成',
     '录屏帧序列、音频产物、品牌素材——都可重新生成'),
]

# 参考资料：每篇一句话
DOC_NOTES = {
    'skills/cli-intro-video/SKILL.md': '这套流程的入口：什么时候用、怎么用。',
    'docs/cli-video-skill-plan.md': '演进计划：素材层怎么生成、改文案为什么难、引擎有无硬编码、下一步做什么。',
    'docs/film-refresh-playbook.md': '改片手册：CLI 变了以后，片子跟着改的顺序、每环改什么、踩过的坑。',
    'docs/film-refresh-io.md': '改片手册（二）：输入输出结构、手动重跑路径、读音错读怎么办。',
    'skills/cli-intro-video/references/workflow.md': '工作流详解：六步各自在做什么。',
    'skills/cli-intro-video/references/profile-schema.md': 'profile 每个字段怎么写、哪些必填。',
    'skills/cli-intro-video/references/pitfalls.md': '踩过的坑：为什么不能手算列宽。',
    'skills/lucid/SKILL.md': 'lucid 引擎的入口。',
    'skills/lucid/PROVENANCE.md': '来源与授权说明。',
    'skills/lucid/capabilities/README.md': '宿主能力总览：配音、转写等。',
    'skills/lucid/capabilities/mcode/voice.md': '配音能力怎么用、退路是什么。',
    'skills/lucid/capabilities/mcode/long-commands.md': '长命令怎么执行。',
    'skills/lucid/references/engine.md': '引擎接口：镜头代码怎么写、怎么调试。',
    'skills/lucid/references/assets.md': '素材：怎么准备、怎么引用。',
    'skills/lucid/references/audio.md': '配音、配乐与响度。',
    'skills/lucid/references/craft.md': '工艺：节奏、转场、字幕。',
    'skills/lucid/references/explainer.md': 'explainer 片型指南。',
    'skills/lucid/references/promo.md': 'promo 片型指南。',
    'skills/lucid/references/review.md': 'review 片型指南。',
    'skills/lucid/references/pitfalls.md': '引擎踩过的坑。',
    'skills/lucid/references/shader-background.md': '着色器背景怎么写。',
    'skills/lucid/references/upstream-guide.md': '原版创作指南。',
    'skills/lucid/references/workflow.md': '引擎工作流。',
}

# 内嵌预览时给一句「这文件是干什么的」
NOTES = {
    'profile/spark-cli.json': '工具档案：二进制、构建命令、命令族、素材录制参数与三档画幅的裁剪范围。',
    'profile/facts.json': '画面事实清单：每条写清「画面上写什么」和「怎么核」。',
    'skills/cli-intro-video/scripts/pipeline.py': '流水线：把六步串成一条命令，任一步失败即停。',
    'skills/cli-intro-video/scripts/facts.py': '事实核对器：跑命令、读文件，逐条比对画面事实。',
    'skills/cli-intro-video/scripts/check_crop.py': '裁剪自检：截字、profile↔CARD、几何常量↔真实网格，三项。',
    'skills/cli-intro-video/scripts/check_pron.py': '读音自检：扫出配音稿里的多音字，和期望读音表比对；--ask 会切音频去问实际读音。',
    'skills/cli-intro-video/scripts/refresh.py': '按改动范围重跑：check / voice / shots / assets / all 五条路径，附带跑前检查清单。',
    'skills/cli-intro-video/scripts/record_terminal.py': '终端录制器：真跑命令，出无损 PNG 帧序列与网格 meta.json。',
    'skills/cli-intro-video/scripts/scaffold.py': '脚手架：按 profile 拉起一个新视频工程（只起骨架，数字留空）。',
    'skills/cli-intro-video/scripts/_paths.py': '定位工程、profile、仓库根与 python 解释器。',
    'skills/cli-intro-video/SKILL.md': '这套流程的入口：什么时候用、怎么用。',
    'docs/cli-video-skill-plan.md': '演进计划：素材层怎么生成、改文案为什么难、引擎有无硬编码、下一步做什么。',
    'docs/film-refresh-playbook.md': '改片手册：CLI 变了以后，片子跟着改的顺序、每环改什么、踩过的坑。',
    'docs/film-refresh-io.md': '改片手册（二）：输入输出结构、手动重跑路径、读音错读怎么办。',
    'skills/lucid/SKILL.md': 'lucid 引擎入口。',
    'skills/lucid/PROVENANCE.md': '来源与授权说明。',
    'project/web/shots_spark.js': '自写镜头代码：六个镜头，几何常量抄自素材 meta.json。',
    'project/project.json': '片型、画幅、主题、配音、章节与素材清单。',
    'project/script/vo.json': '配音稿与逐句英译。',
    'project/timeline.json': '时间线：章节、场景、逐句时间点。',
    'project/web/index.html': '画面入口：多引一行 shots_spark.js。',
    'project/web/meta.json': '',
}


# ---------------------------------------------------------------- SVG 构件

def svg_chip(x: float, y: float, text: str, file_path: str | None):
    """一个文件小标签；file_path 非空时可点。返回 (svg, 下一个 x)。"""
    w = chip_w(text)
    if file_path:
        fill, stroke, cls, data = CHIP_BG, '#dcd5c8', 'chip', f' data-file="{esc(file_path)}"'
    else:
        fill, stroke, cls, data = CHIP_DIM_BG, '#ece7de', 'chip dim', ''
    s = (f'<g class="{cls}"{data} tabindex="0" role="button">'
         f'<title>{esc(text)}</title>'
         f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="22" rx="4" '
         f'fill="{fill}" stroke="{stroke}"/>'
         f'<text x="{x + 8:.1f}" y="{y + 15.2:.1f}" class="chip-t">{esc(text)}</text>'
         f'</g>')
    return s, x + w + 7


def svg_layer_chips(chips, x0: float, y0: float, width: float):
    """把一排小标签折行摆放，返回 (svg, 用了几行)。"""
    out, x, y, row = [], x0, y0, 0
    for file_path, label in chips:
        w = chip_w(label)
        if x > x0 and x + w > x0 + width:
            x = x0
            y += 27
            row += 1
        s, x = svg_chip(x, y, label, file_path or None)
        out.append(s)
    return ''.join(out), row + 1


def chip_label(label: str, file_path: str, mode: str, scan: Scan) -> str:
    """小标签的显示文本。帧数来自素材的 meta.json，不写死。"""
    if mode == 'fixed':
        return label
    if mode == 'frames':
        meta = VIDEO / file_path
        try:
            n = json.loads(meta.read_text(encoding='utf-8')).get('total_frames', 0)
        except (OSError, ValueError):
            n = 0
        return f'{label}  {n} 帧'
    return label


def layer_stat(path: str, scan: Scan) -> str:
    """一层的规模统计。"""
    if path.startswith('project/web/img'):
        total = 0
        for name in ASSET_NAMES:
            meta = VIDEO / f'project/web/img/{name}/meta.json'
            try:
                total += json.loads(meta.read_text(encoding='utf-8')).get('total_frames', 0)
            except (OSError, ValueError):
                pass
        return f'{len(ASSET_NAMES)} 个素材 · {fmt_int(total)} 帧'
    if path.startswith('project/out'):
        try:
            pj = json.loads((VIDEO / 'project' / 'project.json').read_text(encoding='utf-8'))
            fmts = list((pj.get('formats') or {'main': pj.get('canvas')}).keys())
            sec = pj.get('target_sec')
        except (OSError, ValueError):
            fmts, sec = [], None
        tail = f' · {sec} 秒' if sec else ''
        return f'{len(fmts)} 画幅{tail}'
    prefix = path.split(' ＋ ')[0].rstrip('/')
    files = [f for f in scan.tracked if f == prefix or f.startswith(prefix + '/')]
    n = len(files)
    if path.startswith('project/web/'):
        # 素材层单独算；镜头层含 project/web/img 的静帧
        n = len([f for f in files if not f.startswith('project/web/img/')])
    return f'{n} 文件'


def svg_layers(scan: Scan) -> str:
    """图 1：分层架构图。压缩版——每层只画一行代表文件，其余归到「还有 N 个」。

    层框贴着 viewBox 的左右边界（0 与 1160），和同页的思路卡、引擎链路图落在
    同一条竖线上。
    """
    W = 1160
    X, LW = 0, 1160
    LH, GAP = 64, 42
    TOP = 26

    blocks, y = [], TOP
    for i, (no, name, path, chips) in enumerate(LAYERS):
        stat = layer_stat(path, scan)
        labelled = [(fp, chip_label(lbl, fp, mode, scan)) for lbl, fp, mode in chips]

        # 一行放得下就放几个，剩下的折成「还有 N 个」
        chips_svg, x, shown = '', X + 64 + int(vw(path, 12)) + 16, 0
        rest = []
        for fp, label in labelled:
            w = chip_w(label)
            if x + w > X + LW - 16:
                rest.append((fp, label))
                continue
            one, x = svg_chip(x, y + 36, label, fp or None)
            chips_svg += one
            shown += 1
        if rest:
            more = f'还有 {len(rest)} 个'
            w = chip_w(more)
            if x + w > X + LW - 16:
                x = X + LW - 16 - w
            one, x = svg_chip(x, y + 36, more, None)
            chips_svg += one

        blocks.append(f'''
  <g class="layer">
    <rect x="{X}" y="{y}" width="{LW}" height="{LH}" rx="10"
          fill="{PANEL}" stroke="{RULE}"/>
    <circle cx="{X + 22}" cy="{y + 22}" r="11" fill="{ACCENT}"/>
    <text x="{X + 22}" y="{y + 26}" class="l-no" text-anchor="middle">{no}</text>
    <text x="{X + 42}" y="{y + 27}" class="l-name">{esc(name)}</text>
    <text x="{X + LW - 16}" y="{y + 27}" class="l-stat">{esc(stat)}</text>
    <text x="{X + 42}" y="{y + 50}" class="l-path">{esc(path)}</text>
    {chips_svg}
  </g>''')
        if i < len(LAYERS) - 1:
            ax = X + LW / 2
            ay0, ay1 = y + LH, y + LH + GAP - 8
            blocks.append(f'''
  <g class="flow">
    <path d="M {ax:.0f} {ay0:.0f} L {ax:.0f} {ay1 - 6:.0f}" stroke="{ACCENT}" stroke-width="1.4"/>
    <path d="M {ax - 4.5:.0f} {ay1 - 10:.0f} L {ax:.0f} {ay1:.0f} L {ax + 4.5:.0f} {ay1 - 10:.0f}"
          fill="none" stroke="{ACCENT}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="{ax + 12:.0f}" y="{ay0 + GAP / 2 + 1:.0f}" class="f-label">{esc(FLOW[i])}</text>
  </g>''')
        y += LH + GAP

    height = y - GAP + 18
    return f'''<svg viewBox="0 0 {W} {height}" class="diagram" role="img"
     aria-label="视频工作流分层架构图：配置层、工作流层、素材层、镜头层、引擎层、产物层">
{''.join(blocks)}
</svg>'''


def svg_assets(meta: dict) -> str:
    """图 2：终端素材是怎么来的——四步链路。"""
    W = 1160
    BW, GAP = 260, 40
    X0, Y, BH = 0, 24, 212
    H = Y + BH + 26

    steps = [
        ('① 声明', 'profile/spark-cli.json',
         ['assets.<名>.command', 'assets.<名>.capture', 'cols / rows / fps', 'out_width / seq_sec'],
         '要录哪条命令、录多大'),
        ('② 真跑', 'record_terminal.py',
         ['真的执行一次命令', '采集 stdout / stderr', '超采样渲染成 PNG', '逐字显现，节奏合成'],
         '不是画的，是录的'),
        ('③ 落帧', 'project/web/img/<名>/',
         ['0001.png … N.png', 'meta.json 写网格', 'cell: cw / ch', 'pad_x / top'],
         '无损帧序列＋网格'),
        ('④ 对齐', 'shots_spark.js',
         ['CH = 30.1871', 'TOP = 51.0204', 'COLW = 13.1803', 'PADX = 18.7075'],
         '几何常量抄自 meta.json'),
    ]

    boxes = []
    for i, (title, path, lines, tail) in enumerate(steps):
        x = X0 + i * (BW + GAP)
        last = (i == len(steps) - 1)
        # 标题拆成「编号 + 名称」：编号用强调色，名称用黑体。
        # 用 tspan 让浏览器自己排两者间距，不去猜编号的实际字宽。
        num, label = title.split(' ', 1)
        boxes.append(f'''
  <g class="as">
    <rect x="{x}" y="{Y}" width="{BW}" height="{BH}" rx="9" fill="{PANEL}" stroke="{RULE}"/>
    <text x="{x + 15}" y="{Y + 30}" class="as-t"><tspan class="as-num">{esc(num)}</tspan> {esc(label)}</text>
    <text x="{x + 15}" y="{Y + 52}" class="as-p">{esc(path)}</text>
    <line x1="{x + 15}" y1="{Y + 64}" x2="{x + BW - 15}" y2="{Y + 64}" stroke="{RULE}" stroke-width="1"/>
    {"".join(f'<text x="{x + 15}" y="{Y + 88 + j * 26}" class="as-l">{esc(t)}</text>' for j, t in enumerate(lines))}
    <text x="{x + 15}" y="{Y + BH - 18}" class="as-tail">{esc(tail)}</text>
  </g>''')
        if not last:
            ax0 = x + BW + 5
            ax1 = x + BW + GAP - 5
            ay = Y + BH / 2
            boxes.append(f'''
  <path d="M {ax0} {ay} L {ax1 - 5} {ay}" stroke="{ACCENT}" stroke-width="1.8"/>
  <path d="M {ax1 - 9} {ay - 4} L {ax1} {ay} L {ax1 - 9} {ay + 4}" fill="none"
        stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>''')

    return f'''<svg viewBox="0 0 {W} {H}" class="diagram" role="img"
     aria-label="终端素材的来源链路：profile 声明、record_terminal 真跑、落成帧序列、镜头代码对齐网格">
{''.join(boxes)}
</svg>'''


def svg_engine() -> str:
    """图：lucid 引擎怎么把代码变成一支片。

    盒子的左右外缘贴着 viewBox 边界（0 与 1160），这样整张图和上面那排思路卡
    的左右边缘落在同一条线上——两排并排看是对齐的。
    """
    W = 1160
    BW, GAP = 208, 30
    X0, Y, BH = 0, 26, 120
    H = Y + BH + 30

    stages = [
        ('输入', 'project.json', 'shots_*.js 镜头代码', 'vo.json 配音稿'),
        ('预检', 'lint.py 合同', '页面预检查 NaN', 'layout.py 版面'),
        ('渲染', '逐帧 render(t)', '画布 → JPEG', '管道给 ffmpeg'),
        ('合成', '拼接全部分段', '混入 mix_final.wav', '两档互不复用'),
        ('验收', 'checkup.py 体检', '硬伤 / 可选提示', 'deliver.py 核对表'),
    ]

    boxes = []
    for i, (title, *lines) in enumerate(stages):
        x = X0 + i * (BW + GAP)
        boxes.append(f'''
  <g class="en">
    <rect x="{x}" y="{Y}" width="{BW}" height="{BH}" rx="9" fill="{PANEL}" stroke="{RULE}"/>
    <text x="{x + 16}" y="{Y + 30}" class="en-t">{esc(title)}</text>
    {"".join(f'<text x="{x + 16}" y="{Y + 60 + j * 25}" class="en-l">{esc(t)}</text>' for j, t in enumerate(lines))}
  </g>''')
        if i < len(stages) - 1:
            ax0, ax1 = x + BW + 4, x + BW + GAP - 4
            ay = Y + BH / 2
            boxes.append(f'''
  <path d="M {ax0} {ay} L {ax1 - 5} {ay}" stroke="{ACCENT}" stroke-width="1.8"/>
  <path d="M {ax1 - 9} {ay - 4} L {ax1} {ay} L {ax1 - 9} {ay + 4}" fill="none"
        stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>''')

    return f'''<svg viewBox="0 0 {W} {H}" class="diagram" role="img"
     aria-label="lucid 引擎出片链路：输入、预检、逐帧渲染、合成、体检与交付">
{''.join(boxes)}
</svg>'''


def diff_summary():
    """实算原件与工作副本的差异。

    分类口径：
      共同文件  —— 两边同名，逐字节比较；
      手写新增  —— 工作副本有、原件没有，且是人写的（镜头代码）；
      工具生成  —— 工作副本有、原件没有，由录制/时间线/配音等工具产出。
    """
    excl = {'__pycache__', '.venv', 'out', 'frames', '.git'}
    handmade = {'web/shots_spark.js'}

    def collect(root: Path):
        out = {}
        for p in root.rglob('*'):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if any(part in excl for part in rel.parts):
                continue
            out[str(rel)] = p
        return out

    tpl = collect(VIDEO / 'skills/lucid' / 'template')
    prj = collect(VIDEO / 'project')

    common = sorted(set(tpl) & set(prj))
    same, differ = [], []
    for rel in common:
        (same if tpl[rel].read_bytes() == prj[rel].read_bytes() else differ).append(rel)

    only_prj = sorted(set(prj) - set(tpl))
    hand = [f for f in only_prj if f in handmade]
    gen = [f for f in only_prj if f not in handmade]

    buckets: dict[str, list[str]] = {}
    for rel in same:
        key = rel.split('/')[0] if '/' in rel else '（根目录）'
        buckets.setdefault(key, []).append(rel)

    return {
        'tpl_total': len(tpl),
        'prj_total': len(prj),
        'common': len(common),
        'same': len(same),
        'differ': len(differ),
        'differ_files': differ,
        'only_prj': len(only_prj),
        'hand': hand,
        'gen': len(gen),
        'buckets': sorted(buckets.items(), key=lambda kv: -len(kv[1])),
    }


def svg_diff(d: dict) -> str:
    """图 3：框架原件与工作副本的关系。"""
    W, H = 1160, 392
    bucket_text = ' · '.join(f'{k}/ {len(v)}' for k, v in d['buckets'][:6])
    differ_text = ' · '.join(d['differ_files'])

    return f'''<svg viewBox="0 0 {W} {H}" class="diagram" role="img"
     aria-label="框架原件与工作副本的差异：共同 {d['common']} 个文件，其中 {d['same']} 个逐字节相同">
  <g class="dp">
    <rect x="0" y="24" width="530" height="72" rx="9" fill="{PANEL}" stroke="{RULE}"/>
    <text x="20" y="50" class="d-head">原件 · skills/lucid/template/</text>
    <text x="20" y="74" class="d-num2">{d['tpl_total']} 个文件</text>
    <rect x="630" y="24" width="530" height="72" rx="9" fill="{PANEL}" stroke="{RULE}"/>
    <text x="650" y="50" class="d-head">工作副本 · project/</text>
    <text x="650" y="74" class="d-num2">{d['prj_total']} 个文件（{d['common']} ＋ {d['only_prj']}）</text>
    <path d="M 530 60 L 596 60" stroke="{RULE}" stroke-width="1.6"/>
    <path d="M 590 56 L 596 60 L 590 64" fill="none" stroke="{RULE}"
          stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M 630 60 L 564 60" stroke="{RULE}" stroke-width="1.6"/>
    <path d="M 570 56 L 564 60 L 570 64" fill="none" stroke="{RULE}"
          stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="580" y="44" class="d-status2" text-anchor="middle">共同 {d['common']}</text>

  <g class="dsec">
    <text x="0" y="142" class="d-sech">共同 {d['common']} 个文件</text>
    <path d="M 4 166 L 4 224" stroke="{RULE}" stroke-width="1.3"/>
    <path d="M 4 176 L 16 176" stroke="{RULE}" stroke-width="1.3"/>
    <text x="22" y="180" class="d-item">{d['same']} 个逐字节相同</text>
    <text x="200" y="180" class="d-num3">{esc(bucket_text)}</text>
    <path d="M 4 220 L 16 220" stroke="{ACCENT}" stroke-width="1.3"/>
    <text x="22" y="224" class="d-item-a">{d['differ']} 个不同</text>
    <text x="200" y="224" class="d-num3">{esc(differ_text)}</text>
  </g>

  <g class="dsec">
    <text x="0" y="276" class="d-sech">工作副本独有 {d['only_prj']} 个文件</text>
    <path d="M 4 300 L 4 358" stroke="{RULE}" stroke-width="1.3"/>
    <path d="M 4 310 L 16 310" stroke="{ACCENT}" stroke-width="1.3"/>
    <text x="22" y="314" class="d-item-a">{len(d['hand'])} 个手写</text>
    <text x="200" y="314" class="d-num3">{esc(' · '.join(d['hand']))}</text>
    <path d="M 4 354 L 16 354" stroke="{RULE}" stroke-width="1.3"/>
    <text x="22" y="358" class="d-item">{d['gen']} 个工具生成</text>
    <text x="200" y="358" class="d-num3">web/project.js · web/timeline.js · timeline.json · web/img/** · audio/** · assets/**</text>
  </g>

  <text x="0" y="386" class="d-foot">框架升级时只需保住 3 个手写文件（project.json、script/vo.json、shots_spark.js），其余重跑工具即可恢复。</text>
</svg>'''


# ---------------------------------------------------------------- 预览数据

def build_preview(scan: Scan):
    """内嵌可预览文件的正文。同内容只存一份（哈希去重）。"""
    blobs: dict[str, str] = {}
    items = {}
    for rel in scan.tracked:
        if not scan.text[rel] or rel == Scan.SELF:
            continue
        p = VIDEO / rel
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8', errors='replace')
        truncated = False
        if len(raw.encode('utf-8')) > MAX_INLINE:
            lines = raw.splitlines()
            raw = '\n'.join(lines[:HEAD_LINES])
            truncated = True
        key = hashlib.sha1(raw.encode('utf-8')).hexdigest()
        blobs[key] = raw
        items[rel] = {
            'blob': key,
            'bytes': scan.bytes[rel],
            'truncated': truncated,
            'note': NOTES.get(rel, ''),
        }

    # 素材网格元数据不入库，但它是几何常量的唯一来源，单独特例收录
    for name in ASSET_NAMES:
        rel = f'project/web/img/{name}/meta.json'
        p = VIDEO / rel
        if p.exists() and rel not in items:
            raw = p.read_text(encoding='utf-8', errors='replace')
            key = hashlib.sha1(raw.encode('utf-8')).hexdigest()
            blobs[key] = raw
            items[rel] = {
                'blob': key,
                'bytes': p.stat().st_size, 'truncated': False,
                'note': '录制时写下的真实网格（cell 字段）：镜头代码的几何常量抄自这里。此文件不入库，重录素材后重生成。',
            }
    return blobs, items


# ---------------------------------------------------------------- 页面

CSS = """
:root{
  --bg:#f7f5f0; --panel:#fffdf9; --ink:#1d1b18; --ink2:#6d6862;
  --rule:#e3ded4; --accent:#a8431f; --accent-soft:#f6e7e1;
  --mono:'JetBrains Mono',Menlo,Consolas,monospace;
  --serif:'DM Serif Display','Songti SC','Noto Serif CJK SC','Source Han Serif SC',serif;
  --sans:'Outfit','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font-family:var(--sans);font-size:17px;line-height:1.62;font-weight:300;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1376px;margin:0 auto;padding:0 28px 140px}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(168,67,31,.28)}
a:hover{border-bottom-color:var(--accent)}
code,kbd,pre{font-family:var(--mono)}
h1,h2,h3{font-family:var(--serif);font-weight:400;letter-spacing:.01em}
h1{font-size:44px;line-height:1.18;margin:0 0 14px}
h2{font-size:29px;line-height:1.3;margin:0 0 8px}
h3{font-size:20px;line-height:1.4;margin:0 0 6px}
p{margin:0 0 14px}
.eyebrow{font-family:var(--mono);font-size:12.5px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--accent);margin:0 0 18px}
.lede{font-size:19px;line-height:1.62;color:var(--ink2);margin:0 0 26px}
.masthead{padding:64px 0 40px;border-bottom:1px solid var(--rule);margin-bottom:46px}
section{margin-bottom:54px}
.caption{font-size:14.5px;line-height:1.58;color:var(--ink2);margin:0 0 20px}
.caption b{color:var(--ink);font-weight:500}
figure{margin:0 0 22px}
/* 整页一栏：文字、卡片、图都用同一个 1320px 的栏宽，左右边缘天然对齐 */
figure.fig-wide{margin-bottom:26px}
.diagram{width:100%;height:auto;display:block;overflow:visible}
.diagram text{font-family:var(--sans);fill:var(--ink)}
.l-no{font-family:var(--mono);font-size:13px;fill:#fff;font-weight:500}
.l-name{font-size:18px;font-weight:500;fill:var(--ink)}
.l-path{font-family:var(--mono);font-size:13px;fill:var(--ink2)}
.l-stat{font-family:var(--mono);font-size:13.5px;fill:var(--ink2);text-anchor:end}
.chip-t{font-family:var(--mono);font-size:12.5px;fill:var(--ink)}
.chip{cursor:pointer}
.chip.dim{cursor:default}
.chip:hover rect{fill:#e8e2d6;stroke:var(--accent)}
.chip:focus{outline:none}
.chip:focus rect{stroke:var(--accent);stroke-width:1.6}
.f-label{font-size:12.5px;fill:var(--accent)}
/* ---- Hero 流程卡 ---- */
.flow{display:flex;align-items:stretch;margin-top:28px}
.flow-card{flex:1 1 0;min-width:0;background:var(--panel);border:1px solid var(--rule);
  border-radius:10px;padding:13px 12px 11px;display:flex;flex-direction:column}
.fc-top{display:flex;align-items:center;gap:7px;margin-bottom:6px}
.fc-no{width:19px;height:19px;border-radius:50%;background:var(--accent);color:#fff;
  font-family:var(--mono);font-size:11px;display:flex;align-items:center;
  justify-content:center;flex:none}
.fc-name{font-family:var(--mono);font-size:14.5px;color:var(--ink)}
.fc-script{font-family:var(--mono);font-size:11px;color:var(--ink2);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:7px}
.fc-desc{font-size:13.5px;line-height:1.48;color:var(--ink);margin:0 0 8px;flex:1 1 auto}
.fc-io{font-family:var(--mono);font-size:11px;color:var(--ink2);line-height:1.75;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fc-io .k{color:var(--accent);margin-right:4px}
.fc-gate{margin-top:9px;font-family:var(--mono);font-size:11px;text-align:center;
  padding:3px 0;border-radius:4px}
.fc-gate.fail{background:var(--accent-soft);color:var(--accent)}
.fc-gate.pass{background:#efede7;color:var(--ink2)}
.flow-arrow{flex:0 0 20px;display:flex;align-items:center;justify-content:center}
/* ---- 素材链路图 ---- */
/* 块标题用黑体（无衬线），跟页面正文和分层图的层名一致，不跟参数名用等宽 */
.as-num{font-family:var(--sans);font-size:18px;font-weight:500;fill:var(--accent)}
.as-t{font-family:var(--sans);font-size:18px;font-weight:500;fill:var(--ink)}
.as-p{font-family:var(--mono);font-size:13.5px;fill:var(--ink)}
.as-l{font-family:var(--mono);font-size:13.5px;fill:var(--ink2)}
.as-tail{font-size:14px;fill:var(--ink)}
/* ---- 真实值 vs 名义值 ---- */
.geom{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--rule);
  border:1px solid var(--rule);border-radius:10px;overflow:hidden;margin:22px 0 0}
.geom div{background:var(--panel);padding:14px 16px}
.geom .gk{display:block;font-family:var(--mono);font-size:12px;color:var(--ink2);
  letter-spacing:.04em;margin-bottom:5px}
.geom .gv{font-family:var(--mono);font-size:14.5px;color:var(--ink)}
.geom .warn .gv{color:var(--accent)}
.geom .warn .gk{color:var(--accent)}
/* ---- 总体思路卡片 ---- */
.ideas{display:flex;align-items:stretch;margin-top:20px}
.idea{flex:1 1 0;min-width:0;background:var(--panel);border:1px solid var(--rule);
  border-radius:10px;padding:13px 12px 11px;display:flex;flex-direction:column}
.id-top{display:flex;align-items:center;gap:7px;margin-bottom:7px}
.id-no{width:19px;height:19px;border-radius:50%;background:var(--accent);color:#fff;
  font-family:var(--mono);font-size:11px;display:flex;align-items:center;
  justify-content:center;flex:none}
.id-title{font-family:var(--serif);font-size:15.5px;line-height:1.3;color:var(--ink)}
.id-body{font-size:13px;line-height:1.55;color:var(--ink2);margin:0 0 9px}
.id-mech{margin-top:auto;font-family:var(--mono);font-size:11px;line-height:1.55;
  color:var(--ink);padding-left:9px;border-left:2px solid var(--accent)}
pre.snippet{margin:0 0 14px;font-size:13.5px;color:var(--ink)}
.en-t{font-family:var(--sans);font-size:18px;font-weight:500;fill:var(--ink)}
.en-l{font-family:var(--mono);font-size:13.5px;fill:var(--ink2)}
/* ---- 参考资料 ---- */
.doc-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--rule);
  border:1px solid var(--rule);border-radius:10px;overflow:hidden}
.doc-card{background:var(--panel);padding:10px 15px;display:grid;gap:2px;
  cursor:pointer;align-content:center}
.doc-card:hover{background:#fbf8f3}
.doc-card:hover .dc-name{color:var(--accent)}
.dc-head{display:flex;align-items:baseline;gap:10px}
.dc-name{font-family:var(--mono);font-size:13.5px;color:var(--ink)}
.dc-dir{font-family:var(--mono);font-size:11px;color:var(--ink2);
  margin-left:auto;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dc-note{font-size:14px;color:var(--ink2);line-height:1.45}
.d-head{font-family:var(--mono);font-size:14.5px;fill:var(--ink)}
.d-num2{font-family:var(--mono);font-size:13px;fill:var(--ink2)}
.d-num3{font-family:var(--mono);font-size:12.5px;fill:var(--ink2)}
.d-status2{font-family:var(--mono);font-size:12.5px;fill:var(--ink2)}
.d-sech{font-family:var(--serif);font-size:18px;fill:var(--ink)}
.d-item{font-family:var(--mono);font-size:14px;fill:var(--ink)}
.d-item-a{font-family:var(--mono);font-size:14px;fill:var(--accent)}
.d-foot{font-size:13.5px;fill:var(--ink2)}
table{width:100%;border-collapse:collapse;font-size:15px}
th{font-family:var(--mono);font-size:12.5px;font-weight:400;letter-spacing:.06em;
  text-transform:uppercase;color:var(--ink2);text-align:left;
  padding:0 14px 9px 0;border-bottom:1px solid var(--rule)}
td{padding:10px 14px 10px 0;border-bottom:1px solid var(--rule);
  vertical-align:top;line-height:1.55}
td:last-child,th:last-child{padding-right:0}
td.mono,th.mono{font-family:var(--mono);font-size:13px}
td.num{font-family:var(--mono);font-size:13px;text-align:right;white-space:nowrap;color:var(--ink2)}
th.num{text-align:right}
table.modules{table-layout:fixed}
table.modules td:nth-child(1){width:62px;white-space:nowrap}
table.modules td:nth-child(2){width:92px;white-space:nowrap}
table.modules td:nth-child(3){width:30%;word-break:break-all}
table.modules td:nth-child(4){width:148px;white-space:nowrap}
details.mod{border:1px solid var(--rule);border-radius:10px;background:var(--panel);margin-bottom:12px}
details.mod>summary{cursor:pointer;list-style:none;padding:14px 18px;
  display:grid;grid-template-columns:62px 1fr auto;gap:16px;align-items:baseline}
details.mod>summary::-webkit-details-marker{display:none}
details.mod>summary::after{content:'＋';font-family:var(--mono);color:var(--ink2);
  position:absolute;right:18px}
details.mod[open]>summary::after{content:'−'}
details.mod>summary:hover .m-name{color:var(--accent)}
.m-layer{font-family:var(--mono);font-size:12px;color:var(--accent);letter-spacing:.05em}
.m-name{font-family:var(--serif);font-size:19px;color:var(--ink);transition:color .15s}
.m-path{font-family:var(--mono);font-size:12.5px;color:var(--ink2);grid-column:2;
  margin-top:-6px}
.m-count{font-family:var(--mono);font-size:12.5px;color:var(--ink2);white-space:nowrap}
.m-role{padding:0 18px 12px 96px;font-size:15px;color:var(--ink2);line-height:1.55}
.m-role b{color:var(--ink);font-weight:500}
.flist{padding:0 18px 6px 96px}
.flist table{font-size:13.5px}
.flist th{font-size:11.5px;padding-bottom:7px}
.flist td{padding:6px 14px 6px 0}
.filebtn{font-family:var(--mono);font-size:13px;background:none;border:none;
  padding:0;color:var(--ink);cursor:pointer;text-align:left;border-bottom:1px solid transparent}
.filebtn:hover{color:var(--accent);border-bottom-color:rgba(168,67,31,.4)}
.filebtn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.bin{font-family:var(--mono);font-size:13px;color:var(--ink2)}
pre{margin:0;padding:16px 18px;background:#faf8f4;border:1px solid var(--rule);
  border-radius:8px;overflow:auto;max-height:620px;font-size:13px;line-height:1.62;
  white-space:pre;tab-size:4}
/* ---- 文件抽屉 ---- */
/* 遮罩只做视觉压暗，不拦截指针：抽屉开着时页面照样能点、能选文件 */
.dw-backdrop{position:fixed;inset:0;background:rgba(29,27,24,.20);opacity:0;
  pointer-events:none;transition:opacity .24s ease;z-index:40}
.dw-backdrop.open{opacity:1}
.dw{position:fixed;top:0;right:0;height:100vh;width:min(880px,64vw);
  background:var(--panel);border-left:1px solid var(--rule);
  box-shadow:-20px 0 50px rgba(29,27,24,.10);
  transform:translateX(101%);transition:transform .28s cubic-bezier(.22,.61,.36,1);
  z-index:50;display:flex;flex-direction:column;visibility:hidden;
  transition:transform .28s cubic-bezier(.22,.61,.36,1),visibility 0s linear .28s}
.dw.open{transform:translateX(0);visibility:visible;
  transition:transform .28s cubic-bezier(.22,.61,.36,1),visibility 0s}
.dw.resizing{transition:none}
/* 左边的手柄：拖它改抽屉宽度 */
.dw-resize{position:absolute;left:-5px;top:0;bottom:0;width:11px;cursor:ew-resize;
  z-index:2;display:flex;align-items:center;justify-content:center}
.dw-resize::after{content:'';width:4px;height:54px;border-radius:2px;background:#cfc6b4;
  transition:background .15s}
.dw-resize:hover::after{background:var(--accent)}
.dw-resize:focus-visible{outline:2px solid var(--accent);outline-offset:0}
body.resizing{cursor:ew-resize;user-select:none}
.dw-head{display:flex;align-items:flex-start;gap:14px;padding:22px 24px 14px;
  border-bottom:1px solid var(--rule)}
.dw-eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.08em;
  color:var(--accent);margin:0 0 5px}
.dw-title{font-family:var(--serif);font-size:23px;line-height:1.3;margin:0;
  word-break:break-all;color:var(--ink)}
.dw-close{flex:none;width:30px;height:30px;border-radius:6px;border:1px solid var(--rule);
  background:transparent;color:var(--ink2);cursor:pointer;margin-left:auto;padding:0;
  display:flex;align-items:center;justify-content:center}
.dw-close svg{display:block}
.dw-close:hover{border-color:var(--accent);color:var(--accent)}
.dw-close:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.dw-meta{display:grid;grid-template-columns:74px 1fr;gap:7px 16px;margin:0;
  padding:16px 24px 4px}
.dw-meta dt{font-family:var(--mono);font-size:12px;color:var(--ink2);letter-spacing:.04em}
.dw-meta dd{margin:0;font-size:14px;line-height:1.5;color:var(--ink);word-break:break-all}
.dw-meta dd.mono{font-family:var(--mono);font-size:13px;color:var(--ink2)}
.dw-note{font-size:14.5px;color:var(--ink2);line-height:1.55;margin:12px 24px 10px;padding:0}
.dw-note b{color:var(--ink);font-weight:500}
.dw-warn{font-size:13.5px;color:var(--accent);margin:0 24px 10px}
.dw-warn a{color:var(--accent)}
.dw-body{flex:1 1 auto;min-height:0;overflow:auto;padding:0 24px 4px}
.dw-body pre{max-height:none;border-radius:8px}
.dw-foot{display:flex;align-items:center;gap:14px;padding:13px 24px;
  border-top:1px solid var(--rule);font-size:13.5px}
.dw-foot a{font-size:13.5px}
.dw-hint{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--ink2)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:26px}
.note{border-left:2px solid var(--accent);padding:2px 0 2px 16px;
  font-size:15px;line-height:1.6;color:var(--ink2);margin:22px 0}
.note b{color:var(--ink);font-weight:500}
footer{border-top:1px solid var(--rule);padding-top:22px;margin-top:60px;
  font-size:14px;color:var(--ink2);line-height:1.65}
footer code{font-size:11px}
@media (max-width:1080px){
  .flow{flex-wrap:wrap;gap:10px}
  .flow-card{flex:1 1 30%}
  .ideas{flex-wrap:wrap;gap:10px}
  .idea{flex:1 1 30%}
  .flow-arrow{display:none}
  .geom{grid-template-columns:1fr}
  .doc-grid{grid-template-columns:1fr}
}
@media (max-width:820px){
  h1{font-size:31px} h2{font-size:23px}
  .two{grid-template-columns:1fr}
  details.mod>summary{grid-template-columns:1fr;gap:4px}
  .m-path,.m-role,.flist{padding-left:18px;margin-left:0}
  .dw{top:auto;bottom:0;right:0;left:0;width:100%;height:86vh;
    border-left:none;border-top:1px solid var(--rule);border-radius:12px 12px 0 0;
    transform:translateY(101%);box-shadow:0 -20px 50px rgba(29,27,24,.12)}
  .dw.open{transform:translateY(0)}
  .dw-resize{display:none}
  .flow-card{flex:1 1 100%}
  .idea{flex:1 1 100%}
}
"""

JS = """
(function () {
  var data = JSON.parse(document.getElementById('preview-data').textContent);
  var blobs = data.blobs, items = data.items, repo = data.repo, branch = data.branch;
  var maxInline = data.max_inline;

  var drawer = document.getElementById('dw');
  var backdrop = document.getElementById('dw-backdrop');
  var closeBtn = document.getElementById('dw-close');
  var handle = document.getElementById('dw-resize');
  var titleEl = document.getElementById('dw-title');
  var eyebrowEl = document.getElementById('dw-eyebrow');
  var pathEl = document.getElementById('dw-path');
  var sizeEl = document.getElementById('dw-size');
  var modEl = document.getElementById('dw-mod');
  var noteEl = document.getElementById('dw-note');
  var warnEl = document.getElementById('dw-warn');
  var codeEl = document.getElementById('dw-code');
  var ghEl = document.getElementById('dw-gh');
  var lastFocus = null;

  function kb(n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1048576).toFixed(2) + ' MB';
  }
  function baseName(p) {
    var i = p.lastIndexOf('/');
    return i < 0 ? p : p.slice(i + 1);
  }

  // ---- 抽屉宽度：默认 min(880px, 64vw)，可拖左边缘调整，宽度记在本地 ----
  var MIN_W = 360, MAX_RATIO = 0.86, WKEY = 'arch-drawer-width';
  function isSheet() { return window.innerWidth <= 820; }
  function readW() {
    try { return parseInt(localStorage.getItem(WKEY) || '', 10) || 0; }
    catch (e) { return 0; }
  }
  function setW(px, save) {
    if (isSheet()) { drawer.style.width = ''; return 0; }
    var max = Math.round(window.innerWidth * MAX_RATIO);
    var w = Math.max(MIN_W, Math.min(Math.round(px), max));
    drawer.style.width = w + 'px';
    handle.setAttribute('aria-valuenow', String(w));
    if (save) { try { localStorage.setItem(WKEY, String(w)); } catch (e) {} }
    return w;
  }
  var saved = readW();
  setW(saved || Math.min(880, Math.round(window.innerWidth * 0.64)), false);

  var dragging = false, dragX = 0, dragW = 0;
  handle.addEventListener('pointerdown', function (e) {
    if (isSheet()) return;
    dragging = true; dragX = e.clientX;
    dragW = drawer.getBoundingClientRect().width;
    drawer.classList.add('resizing');
    document.body.classList.add('resizing');
    try { handle.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  handle.addEventListener('pointermove', function (e) {
    if (!dragging) return;
    setW(dragW + (dragX - e.clientX), false);
  });
  function endDrag(e) {
    if (!dragging) return;
    dragging = false;
    drawer.classList.remove('resizing');
    document.body.classList.remove('resizing');
    try { handle.releasePointerCapture(e.pointerId); } catch (err) {}
    setW(drawer.getBoundingClientRect().width, true);
  }
  handle.addEventListener('pointerup', endDrag);
  handle.addEventListener('pointercancel', endDrag);
  handle.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    var cur = drawer.getBoundingClientRect().width;
    setW(cur + (e.key === 'ArrowLeft' ? 48 : -48), true);
  });
  window.addEventListener('resize', function () {
    if (isSheet()) { drawer.style.width = ''; return; }
    setW(readW() || Math.min(880, Math.round(window.innerWidth * 0.64)), false);
  });
  function open(rel, trigger) {
    var it = items[rel];
    if (!it) return;
    var body = blobs[it.blob] || '';
    var shown = body.split('\\n').length;

    titleEl.textContent = baseName(rel);
    eyebrowEl.textContent = it.module || '—';
    pathEl.textContent = 'video/' + rel;
    sizeEl.textContent = kb(it.bytes) +
      (it.truncated ? ' · 预览前 ' + shown + ' 行' : ' · 全文');
    modEl.textContent = it.module || '—';
    noteEl.innerHTML = it.note ? it.note : '';
    noteEl.style.display = it.note ? '' : 'none';

    var url = 'https://github.com/' + repo + '/blob/' + branch + '/video/' + rel;
    ghEl.href = url;
    if (it.truncated) {
      warnEl.innerHTML = '文件超过 ' + (maxInline / 1024) + ' KB，抽屉里只放前 ' +
        shown + ' 行。完整内容见下方链接。';
    } else {
      warnEl.innerHTML = '';
    }
    warnEl.style.display = it.truncated ? '' : 'none';
    codeEl.textContent = body;

    if (!drawer.classList.contains('open')) {
      lastFocus = trigger || document.activeElement;
      drawer.classList.add('open');
      backdrop.classList.add('open');
      drawer.setAttribute('aria-hidden', 'false');
      closeBtn.focus();
    }
    drawer.querySelector('.dw-body').scrollTop = 0;
  }
  function close() {
    if (!drawer.classList.contains('open')) return;
    drawer.classList.remove('open');
    backdrop.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener('click', function (e) {
    // 点文件：抽屉开着就换内容，没开就弹出来
    var t = e.target.closest('[data-file]');
    if (t) {
      var rel = t.getAttribute('data-file');
      if (rel) { e.preventDefault(); open(rel, t); }
      return;
    }
    if (e.target.closest('#dw-close')) { e.preventDefault(); close(); return; }
    // 点抽屉以外的页面空白处：关掉抽屉
    if (drawer.classList.contains('open') && !drawer.contains(e.target)) close();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { close(); return; }
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var t = e.target.closest('[data-file]');
    if (!t) return;
    e.preventDefault();
    var rel = t.getAttribute('data-file');
    if (rel) open(rel, t);
  });
})();
"""


def skill_of(rel: str) -> str:
    """文件属于哪个 Skill：skills/<skill>/…；docs/ 下的归 docs。"""
    parts = rel.split('/')
    if len(parts) > 2 and parts[0] == 'skills':
        return parts[1]
    if len(parts) > 1:
        return parts[0]
    return '—'


def hero_cards() -> str:
    """Hero 里的六步流程卡。"""
    arrow = ('<div class="flow-arrow" aria-hidden="true">'
             '<svg width="14" height="14" viewBox="0 0 14 14">'
             '<path d="M4 2 L9 7 L4 12" fill="none" stroke="' + ACCENT +
             '" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
             '</svg></div>')
    cards = []
    for i, (step, script, inp, outp, gate, desc) in enumerate(PIPELINE):
        fail = gate.startswith('退出码')
        cards.append(f'''
    <div class="flow-card">
      <div class="fc-top"><span class="fc-no">{i + 1}</span><span class="fc-name">{esc(step)}</span></div>
      <div class="fc-script">{esc(script)}</div>
      <p class="fc-desc">{esc(desc)}</p>
      <div class="fc-io"><span class="k">入</span>{esc(inp)}</div>
      <div class="fc-io"><span class="k">出</span>{esc(outp)}</div>
      <div class="fc-gate {'fail' if fail else 'pass'}">{esc(gate)}</div>
    </div>''')
    return ('<div class="flow">' + arrow.join(cards) + '</div>')


def file_module_map(scan: Scan) -> dict[str, str]:
    """文件 → 所属模块（层 · 模块名），给抽屉里的「所属模块」用。"""
    out: dict[str, str] = {}
    for layer, name, paths, _role in MODULES:
        for f in scan.tracked:
            if f == Scan.SELF:
                continue
            if any(f == p or f.startswith(p.rstrip('/') + '/') for p in paths):
                out.setdefault(f, f'{layer} · {name}')
    for nm in ASSET_NAMES:
        out.setdefault(f'project/web/img/{nm}/meta.json', '素材层 · 终端素材')
    return out


def render(scan: Scan) -> str:
    blobs, items = build_preview(scan)
    diff = diff_summary()
    fmods = file_module_map(scan)
    for rel in items:
        items[rel]['module'] = fmods.get(rel, '—')

    repo_url = git('remote', 'get-url', 'origin')
    repo = repo_url.rstrip('/').split('/')[-1]
    if repo.endswith('.git'):
        repo = repo[:-4]
    owner = repo_url.rstrip('/').split('/')[-2]
    repo = f'{owner}/{repo}'
    branch = git('rev-parse', '--abbrev-ref', 'HEAD')
    commit = git('rev-parse', '--short', 'HEAD')
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    code_n = len(scan.code_files())
    chk_n = scan.cross_check()
    if chk_n != code_n:
        sys.exit('❌ 两种口径的文件数不一致，先把统计口径修好再出图')

    # --- 模块清单：每个模块一个可折叠块，展开是它的文件
    details = []
    for layer, name, paths, role in MODULES:
        prefix = tuple(paths)
        files = [r for r in scan.tracked
                 if r != Scan.SELF
                 and any(r == q or r.startswith(q.rstrip('/') + '/') for q in prefix)]
        txt = [f for f in files if scan.text[f]]
        nbin = len(files) - len(txt)
        stat = f'{len(files)} 文件'
        if nbin:
            stat += f' · {nbin} 个二进制'
        if 'project/web/img' in prefix:
            total = 0
            for nm in ASSET_NAMES:
                mp = VIDEO / f'project/web/img/{nm}/meta.json'
                try:
                    total += json.loads(mp.read_text(encoding='utf-8')).get('total_frames', 0)
                except (OSError, ValueError):
                    pass
            stat = f'{len(files)} 个入库文件（静帧与图标）· {fmt_int(total)} 帧（帧序列不入库）'
        path_label = '、'.join(paths)

        frows = []
        for f in sorted(files):
            if scan.text[f]:
                note = NOTES.get(f, '')
                frows.append(
                    f'<tr><td><button class="filebtn" data-file="{esc(f)}">{esc(Path(f).name)}</button></td>'
                    f'<td class="mono">{esc(str(Path(f).parent))}/</td>'
                    f'<td class="num">{kb(scan.bytes[f])}</td>'
                    f'<td>{esc(note)}</td></tr>')
            else:
                frows.append(
                    f'<tr><td class="bin">{esc(Path(f).name)}</td>'
                    f'<td class="mono">{esc(str(Path(f).parent))}/</td>'
                    f'<td class="num">{kb(scan.bytes[f])}</td>'
                    f'<td class="bin">二进制，不预览</td></tr>')
        # 素材网格元数据：不在入库清单里，单独特例补上
        if 'project/web/img' in prefix:
            for name2 in ASSET_NAMES:
                rel = f'project/web/img/{name2}/meta.json'
                if rel in items:
                    frows.append(
                        f'<tr><td><button class="filebtn" data-file="{esc(rel)}">meta.json</button></td>'
                        f'<td class="mono">project/web/img/{esc(name2)}/</td>'
                        f'<td class="num">{kb(items[rel]["bytes"])}</td>'
                        f'<td>真实网格（cell 字段）——不入库，重录后重生成</td></tr>')

        details.append(f'''
  <details class="mod">
    <summary>
      <span class="m-layer">{esc(layer)}</span>
      <span class="m-name">{esc(name)}</span>
      <span class="m-count">{esc(stat)}</span>
      <span class="m-path">{esc(path_label)}</span>
    </summary>
    <p class="m-role">{esc(role)}</p>
    <div class="flist">
      <table>
        <thead><tr><th>文件</th><th>目录</th><th class="num">大小</th><th>说明</th></tr></thead>
        <tbody>{''.join(frows)}</tbody>
      </table>
    </div>
  </details>''')

    # --- 终端素材：帧数、命令、名义 vs 真实列宽
    metas = {}
    for nm in ASSET_NAMES:
        mp = VIDEO / f'project/web/img/{nm}/meta.json'
        try:
            metas[nm] = json.loads(mp.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            metas[nm] = {}
    total_frames = sum(m.get('total_frames', 0) for m in metas.values())
    hm = metas.get('help') or {}
    hsize = hm.get('size') or [0, 0]
    hcols = hm.get('cols') or 1
    nominal = hsize[0] / hcols if hcols else 0
    real = (hm.get('cell') or {}).get('cw', 0)
    diff_pct = (nominal - real) / nominal * 100 if nominal else 0
    asset_rows = ''.join(
        f'<tr><td class="mono">{esc(nm)}</td>'
        f'<td class="mono">{esc(str(m.get("cmd", "")))}</td>'
        f'<td class="num">{fmt_int(m.get("total_frames", 0))}</td>'
        f'<td class="num">{m.get("duration", 0)} 秒</td>'
        f'<td class="num">{hsize[0] and m.get("size", [0, 0])[0]}×{m.get("size", [0, 0])[1]}</td></tr>'
        for nm, m in metas.items())

    # --- 参考资料（随工程入库的说明文档）
    doc_files = sorted(f for f in scan.tracked
                       if f.endswith('.md')
                       and (f.startswith('skills/') or f.startswith('docs/'))
                       and f != Scan.SELF)
    doc_cards = ''.join(
        f'<div class="doc-card" data-file="{esc(f)}" role="button" tabindex="0">'
        f'<span class="dc-head"><span class="dc-name">{esc(skill_of(f))} · {esc(Path(f).name)}</span>'
        f'<span class="dc-dir">{esc(str(Path(f).parent))}/</span></span>'
        f'<span class="dc-note">{esc(DOC_NOTES.get(f, "随工程入库的说明文档"))}</span>'
        f'</div>' for f in doc_files)

    # --- 差异表
    diff_rows = ''.join(
        f'<tr><td class="mono">{esc(p)}</td><td class="mono">{esc(k)}</td>'
        f'<td>{esc(w)}</td></tr>' for p, k, w in DIFF_FILES)

    payload = json.dumps({'blobs': blobs, 'items': items, 'repo': repo, 'branch': branch,
                         'max_inline': MAX_INLINE, 'head_lines': HEAD_LINES},
                        ensure_ascii=False)
    payload = payload.replace('</', '<\\/').replace('<!--', '<\\u0021--')

    caption3 = (
        '<p class="caption"><b>图 3</b> · <code>skills/lucid/template/</code> 是 lucid 框架的原件，'
        '<code>project/</code> 是它的工作副本。两边同名文件里 '
        f'{diff["same"]} 个逐字节相同，只有 {diff["differ"]} 个不同；'
        f'工作副本独有的 {diff["only_prj"]} 个文件里，只有 1 个是手写的'
        '（<code>web/shots_spark.js</code>），其余都是录制、时间线、配音这些工具的产物。'
        '所以框架升级时可以整目录覆盖，只需要把 3 个手写文件搬回去。</p>')
    hero = hero_cards()
    page = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>spark-cli 介绍片 · 架构与模块图</title>
<meta name="description" content="spark-cli 介绍片视频工程的分层架构、流水线、模块清单与文件预览。">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Outfit:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

  <header class="masthead">
    <p class="eyebrow">spark-cli · 介绍片工程</p>
    <h1>视频工作流的架构与模块</h1>
    <p class="lede">一支 52 秒的中文介绍片，从「工具档案」一路流到「三画幅成片」。
      画面里的每条命令、每个版本号都由脚本在渲染前核对过——
      下面这条流水线跑完，片子才算数。</p>
    {hero}
  </header>

  <section id="lucid">
    <h2>一、lucid 的总体思路</h2>
    <p class="caption">lucid 是「用代码写视频」的引擎。画面不是拖模板拼出来的，是写一段 JavaScript：
      第 t 毫秒这一帧该长什么样，由代码算出来。</p>
    <pre class="snippet">SHOT.S03 = function (ctx, t, S) {{ … }}</pre>
    <p class="caption">引擎负责逐帧渲染、拼片、混音、体检和交付核对；
      片子好不好看，取决于写镜头的人。下面五条是它的总体思路。</p>
    <div class="ideas">
      <div class="idea">
        <div class="id-top"><span class="id-no">1</span><span class="id-title">画面只由时间算出</span></div>
        <p class="id-body">镜头只依赖 t，不存状态、不用随机数——所以能逐帧渲染、分段并行、只重渲改过的镜头。</p>
        <p class="id-mech">lint.py 渲染前拦违规写法</p>
      </div>
      <div class="idea">
        <div class="id-top"><span class="id-no">2</span><span class="id-title">代码就是分镜</span></div>
        <p class="id-body">引擎给的是一套排版与运动的词汇表。写镜头＝登记物件→分区→放主体→出字→登记事件。</p>
        <p class="id-mech">engine.md · explainer/promo/review.md</p>
      </div>
      <div class="idea">
        <div class="id-top"><span class="id-no">3</span><span class="id-title">时间轴决定一切</span></div>
        <p class="id-body">beats / manual / voice 三种模式。讲解片用 voice，画面事件挂在短句上，声音天生对齐。</p>
        <p class="id-mech">timeline.py 同步时间线；tts.py full 合成并转写</p>
      </div>
      <div class="idea">
        <div class="id-top"><span class="id-no">4</span><span class="id-title">草稿迭代，正式档一次</span></div>
        <p class="id-body">草稿半尺寸、快；正式档开运动模糊，并跟草稿逐帧比对查重影。</p>
        <p class="id-mech">render.py 默认草稿／--final 正式；分段指纹决定增量</p>
      </div>
      <div class="idea">
        <div class="id-top"><span class="id-no">5</span><span class="id-title">验收靠机器</span></div>
        <p class="id-body">渲染前预检三道，渲染后体检；硬伤拦住渲染，可选提示只写进报告。</p>
        <p class="id-mech">lint.py → 页面预检 → layout.py；checkup.py 体检</p>
      </div>
    </div>
    <figure class="fig-wide">{svg_engine()}</figure>
  </section>

  <section id="layers">
    <h2>二、分层架构</h2>
    <figure class="fig-wide">{svg_layers(scan)}</figure>
  </section>

  <section id="assets">
    <h2>三、终端素材从哪来</h2>
    <p class="caption"><b>图 2</b> · 画面里那些终端输出不是画的，是<strong>真的跑出来的</strong>。
      profile 声明要录哪条命令，录制器把它执行一遍、按参数渲染成无损 PNG 帧序列，
      帧序列旁边的 <code>meta.json</code> 写下最终分辨率下的真实网格，镜头代码再把这四个数抄过去。
      {total_frames} 帧，全部来自 {len(metas)} 条真实命令。</p>
    <figure class="fig-wide">{svg_assets(metas)}</figure>
    <table>
      <thead><tr><th>素材</th><th>实际执行的命令</th><th class="num">帧数</th><th class="num">时长</th><th class="num">尺寸</th></tr></thead>
      <tbody>{asset_rows}</tbody>
    </table>
    <div class="geom">
      <div><span class="gk">名义列宽</span><span class="gv">{hsize[0]} ÷ {hcols} = {nominal:.4f} px</span></div>
      <div><span class="gk">真实列宽</span><span class="gv">meta.json 的 cell.cw = {real} px</span></div>
      <div class="warn"><span class="gk">差 {diff_pct:.1f}%</span><span class="gv">用名义值，标注线会整体偏掉</span></div>
    </div>
    <p class="caption">素材文本区两侧留了内边距（{hsize[0]}px 宽里文字只占 {(hm.get('cell') or {}).get('text_width', 0)}px），
      所以真实列宽不等于「画幅宽 ÷ 列数」。
      <code>check_crop.py</code> 会拿镜头代码里的几何常量跟 <code>meta.json</code> 逐个比对
      （容差 0.02 像素），对不上就拦住渲染——所以别手算，抄 <code>meta.json</code>。</p>
  </section>

  <section id="diff">
    <h2>四、原件与工作副本</h2>
{caption3}
    <figure class="fig-wide">{svg_diff(diff)}</figure>
    <table>
      <thead><tr><th>文件</th><th>类别</th><th>说明</th></tr></thead>
      <tbody>{diff_rows}</tbody>
    </table>
  </section>

  <section id="modules">
    <h2>五、模块清单</h2>
    <p class="caption">{len(MODULES)} 个模块按层排列，每一项都能展开。
      展开后是这个模块包含的文件、大小与职责，点文件名会滑出抽屉看源码
      （16 KB 以内给全文，更大的只给前 100 行并附 GitHub 链接）。
      抽屉可以拖左边缘调宽；按 <kbd>Esc</kbd>、点关闭按钮或点抽屉外任意处都能关。</p>
    {''.join(details)}
  </section>

  <section id="refs">
    <h2>六、参考资料</h2>
    <p class="caption">随工程一起入库的 {len(doc_files)} 篇说明文档，点任意一篇同样滑出抽屉看内容。</p>
    <div class="doc-grid">{doc_cards}</div>
  </section>

  <footer>
    <p>本页由 <code>video/docs/build_architecture.py</code> 生成，数字来自扫描基线
      （基线提交 <code>{commit}</code>）的真实文件系统扫描；
      文件清单以 <code>git ls-files video</code> 为准（入库文件，工程内生成的产物不在其中）。
      工程改动后重跑脚本即可更新。</p>
  </footer>

</div>

<div class="dw-backdrop" id="dw-backdrop"></div>
<aside class="dw" id="dw" role="dialog" aria-modal="true" aria-hidden="true"
       aria-labelledby="dw-title">
  <div class="dw-resize" id="dw-resize" role="separator" aria-orientation="vertical"
       tabindex="0" aria-label="调整抽屉宽度，拖动或用左右方向键"
       aria-valuemin="360" aria-valuemax="100" aria-valuenow="880"></div>
  <header class="dw-head">
    <div>
      <p class="dw-eyebrow" id="dw-eyebrow">—</p>
      <h2 class="dw-title" id="dw-title">文件</h2>
    </div>
    <button class="dw-close" id="dw-close" type="button" aria-label="关闭抽屉"><svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true"><path d="M2 2 L11 11 M11 2 L2 11" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></button>
  </header>
  <dl class="dw-meta">
    <dt>路径</dt><dd class="mono" id="dw-path"></dd>
    <dt>规模</dt><dd id="dw-size"></dd>
    <dt>模块</dt><dd id="dw-mod"></dd>
  </dl>
  <p class="dw-note" id="dw-note"></p>
  <p class="dw-warn" id="dw-warn" style="display:none"></p>
  <div class="dw-body"><pre id="dw-code"></pre></div>
  <footer class="dw-foot">
    <a id="dw-gh" href="#" target="_blank" rel="noopener">在 GitHub 上看这个文件 ↗</a>
    <span class="dw-hint">Esc 关闭 · 拖左边缘调宽</span>
  </footer>
</aside>

<script type="application/json" id="preview-data">{payload}</script>
<script>{JS}</script>
</body>
</html>
'''
    return page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只校验，不写文件')
    a = ap.parse_args()

    scan = Scan()
    code_n = len(scan.code_files())
    chk_n = scan.cross_check()
    print(f'入库文件 {len(scan.tracked)} 个')
    print(f'代码（.py/.js）{code_n} 个文件')
    print(f'独立复核 find：{chk_n} 个文件')
    if chk_n != code_n:
        sys.exit('❌ 两种口径的文件数不一致，先把统计口径修好再出图')
    print(f'文档（.md）{len(scan.doc_files())} 篇')

    page = render(scan)
    if a.check:
        print(f'页面 {len(page):,} 字节，校验通过（未写入）')
        return
    OUT.write_text(page, encoding='utf-8')
    print(f'✅ 已写出 {OUT.relative_to(REPO)}（{len(page.encode("utf-8")):,} 字节）')


if __name__ == '__main__':
    main()
