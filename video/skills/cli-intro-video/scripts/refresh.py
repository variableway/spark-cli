#!/usr/bin/env python3
"""按「这次改了什么」挑步骤重跑一次片子。

为什么要有这个：`pipeline.py` 把步骤列全了（facts/crop/record/sync/render/deliver），
但**配音那一步不在里面**——配音是 `tts.py` 干的，改完配音稿要自己记得补上，
忘了就会拿旧配音渲出新画面，字幕和声音对不上。

而且不同改动要走的路径不一样：只改画面上的字不该重录终端素材（十分钟级），
只改终端输出才需要。这个脚本把「改了什么 → 跑哪几步 → 跳过哪几步」写死，
顺带把跑之前该检查的东西列出来。

阶段（--stage）：
  check   只跑门禁：事实核对 + 裁剪自检 + 读音自检（静态）。不改任何东西。
  voice   改了配音稿（vo.json）：重录配音 → 重建时间轴 → 读音核对 → 渲染 → 交付核对
  shots   只改了画面字面量（shots_spark.js）：门禁 → 渲染 → 交付核对（不重录配音、不重录素材）
  assets  改了终端输出（命令变了）：重录素材 → 重建时间轴 → 门禁 → 渲染 → 交付核对
  all     全来一遍：重录素材 + 重录配音 + 渲染 + 交付核对

用法：
  python3 scripts/refresh.py --project video/project --profile video/profile --stage voice
  python3 scripts/refresh.py ... --stage shots --final --format all
  python3 scripts/refresh.py ... --stage check --ask

选项：
  --final / --draft   正式档（开运动模糊）还是草稿档（半尺寸快）。默认草稿。
  --format            16x9 / 9x16 / 1x1 / all，默认 all
  --ask               读音自检真的去问 AI（要联网和 mcode-tools）；默认只静态查
  --dry-run           只打印这一步要跑什么，不真跑

退出码：0 走完；1 某一步失败（门禁不过就是不过，不带着问题渲染）。
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import find_project, python_bin, resolve_profile  # noqa: E402

KIT = Path(__file__).resolve().parent

# 每个阶段：(说明, [(标签, 命令模板)])。{py}=工程解释器 {kit}=脚本目录
STAGES = {
    'check': (
        '只跑门禁，不改任何东西：事实核对 → 裁剪自检 → 读音自检（静态）',
        [('facts', ['{py}', '{kit}/facts.py', '--profile', '{profile}', '--project', '{project}']),
         ('crop', ['{py}', '{kit}/check_crop.py', '--profile', '{profile}', '--project', '{project}']),
         ('pron', ['{py}', '{kit}/check_pron.py', '--profile', '{profile}', '--project', '{project}'] + ['--ask']),
         ],
    ),
    'voice': (
        '改了配音稿：重录配音 → 重建时间轴 → 门禁 → 渲染 → 交付核对（终端素材不用重录）',
        [('tts', ['{py}', '{project}/tools/tts.py', 'full']),
         ('sync', ['{py}', '{project}/tools/timeline.py']),
         ('facts', ['{py}', '{kit}/facts.py', '--profile', '{profile}', '--project', '{project}']),
         ('crop', ['{py}', '{kit}/check_crop.py', '--profile', '{profile}', '--project', '{project}']),
         ('pron', ['{py}', '{kit}/check_pron.py', '--profile', '{profile}', '--project', '{project}'] + ['--ask']),
         ('render', ['{py}', '{project}/tools/render.py'] + ['--final'] + ['--format', '{format}']),
         ('deliver', ['{py}', '{project}/tools/deliver.py', '--format', '{format}']),
         ],
    ),
    'shots': (
        '只改了画面字面量：门禁 → 渲染 → 交付核对（配音和终端素材都不动）',
        [('facts', ['{py}', '{kit}/facts.py', '--profile', '{profile}', '--project', '{project}']),
         ('crop', ['{py}', '{kit}/check_crop.py', '--profile', '{profile}', '--project', '{project}']),
         ('pron', ['{py}', '{kit}/check_pron.py', '--profile', '{profile}', '--project', '{project}'] + ['--ask']),
         ('render', ['{py}', '{project}/tools/render.py'] + ['--final'] + ['--format', '{format}']),
         ('deliver', ['{py}', '{project}/tools/deliver.py', '--format', '{format}']),
         ],
    ),
    'assets': (
        '改了终端输出：重录素材 → 重建时间轴 → 门禁 → 渲染 → 交付核对（配音不动）',
        [('record', ['{py}', '{kit}/record_terminal.py', '--help-placeholder']),
         ('sync', ['{py}', '{project}/tools/timeline.py']),
         ('facts', ['{py}', '{kit}/facts.py', '--profile', '{profile}', '--project', '{project}']),
         ('crop', ['{py}', '{kit}/check_crop.py', '--profile', '{profile}', '--project', '{project}']),
         ('pron', ['{py}', '{kit}/check_pron.py', '--profile', '{profile}', '--project', '{project}'] + ['--ask']),
         ('render', ['{py}', '{project}/tools/render.py'] + ['--final'] + ['--format', '{format}']),
         ('deliver', ['{py}', '{project}/tools/deliver.py', '--format', '{format}']),
         ],
    ),
    'all': (
        '全来一遍：重录素材 + 重录配音 → 重建时间轴 → 门禁 → 渲染 → 交付核对',
        [('record', ['{py}', '{kit}/record_terminal.py', '--help-placeholder']),
         ('tts', ['{py}', '{project}/tools/tts.py', 'full']),
         ('sync', ['{py}', '{project}/tools/timeline.py']),
         ('facts', ['{py}', '{kit}/facts.py', '--profile', '{profile}', '--project', '{project}']),
         ('crop', ['{py}', '{kit}/check_crop.py', '--profile', '{profile}', '--project', '{project}']),
         ('pron', ['{py}', '{kit}/check_pron.py', '--profile', '{profile}', '--project', '{project}'] + ['--ask']),
         ('render', ['{py}', '{project}/tools/render.py'] + ['--final'] + ['--format', '{format}']),
         ('deliver', ['{py}', '{project}/tools/deliver.py', '--format', '{format}']),
         ],
    ),
}

# 每个阶段跳过了什么、为什么
SKIPPED = {
    'check': ['渲染', '配音', '素材'],
    'voice': ['终端素材重录（命令输出没变）'],
    'shots': ['配音重录（文案没变）', '终端素材重录'],
    'assets': ['配音重录（文案没变）'],
    'all': [],
}

PRECHECK = """跑之前该确认的（脚本能查的已经自动查了，这几条要人看）：

  1. 二进制是新的：profile.binary.path 指的那个是「改完源码之后」构建的吗？
     二进制比源码旧，事实核对拦的是它，不是画面——先 make build。
  2. 短句数没变：vo.json 里每镜的中文短句数必须等于 en 数组长度。
     短句数一变，镜头里的 ph('Sxx', k) 索引就平移（core.js:263 会静默夹住，不报错）。
  3. 画面文案和配音稿对得上：改了一句就要两处都改（shots_spark.js 的字面量 + vo.json 的 text）。
  4. 多音字：期望读音表（profile.pronunciation.rules）覆盖了稿子里所有多音字。
  5. 终端素材：命令的输出变了吗？变了才需要重录素材（--stage assets）。
"""


def run(cmd, cwd=None, label=''):
    print(f'\n── {label} ──', flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if r.returncode != 0:
        print(f'\n❌ {label} 失败（退出码 {r.returncode}）。停在这一步，不继续渲染。',
              file=sys.stderr)
        raise SystemExit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default=None, help='视频工程目录')
    ap.add_argument('--profile', default=None, help='profile 文件或目录')
    ap.add_argument('--stage', default='check', choices=sorted(STAGES), help='跑哪条路径')
    ap.add_argument('--final', action='store_true', help='正式档（默认草稿档）')
    ap.add_argument('--format', default='all', help='16x9 / 9x16 / 1x1 / all')
    ap.add_argument('--ask', action='store_true', help='读音自检真的去问 AI')
    ap.add_argument('--dry-run', action='store_true', help='只打印要跑什么')
    ap.add_argument('--no-precheck', action='store_true', help='不打印跑前检查清单')
    a = ap.parse_args()

    project = find_project(a.project)
    profile = resolve_profile(a.profile, project)
    py = python_bin(project)

    desc, steps = STAGES[a.stage]
    print(f'改片刷新：{project}')
    print(f'  阶段 {a.stage}：{desc}')
    print(f'  profile {profile} · {"正式档" if a.final else "草稿档"} · 画幅 {a.format}')
    if SKIPPED[a.stage]:
        print('  跳过：' + '、'.join(SKIPPED[a.stage]))
    if not a.no_precheck:
        print('\n' + PRECHECK)

    for label, cmd in steps:
        cmd = [str(c).format(py=py, kit=KIT, project=project, profile=profile,
                             format=a.format) for c in cmd]
        # 「重录素材」要走 pipeline（它按 profile 逐条拼参数）
        if label == 'record':
            cmd = [py, KIT / 'pipeline.py', '--profile', profile, '--project', project,
                   '--only', 'record', '--record']
        if label == 'pron' and not a.ask:
            cmd = [c for c in cmd if c != '--ask']
        if label == 'render' and not a.final:
            cmd = [c for c in cmd if c != '--final']
        if a.dry_run:
            print(f'\n（dry-run）{label}: {" ".join(cmd)}')
            continue
        cwd = str(project) if label in ('tts', 'sync', 'render', 'deliver') else None
        run(cmd, cwd=cwd, label=label)

    if a.dry_run:
        print('\n（dry-run）没有真跑。')
    else:
        print(f'\n✅ 阶段 {a.stage} 走完。成片在 {project}/out/，'
              f'交付核对在 {project}/out/交付核对.md')
    sys.exit(0)


if __name__ == '__main__':
    main()
