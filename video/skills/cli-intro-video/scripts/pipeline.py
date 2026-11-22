#!/usr/bin/env python3
"""流水线：一条命令把「事实核对 → 裁剪自检 → 录制素材 → 渲染 → 交付核对」跑完。

为什么要有这个：lucid 自带的 render.py 会自动同步时间线、音效事件和配乐，
但**不覆盖**素材录制、事实核对和裁剪自检——这三件事是「内容必须真实」这条约束的
落脚处，漏掉就等于没做。所以把整条链接起来，任何一步对不上就停在那一步，
别带着问题渲染。

步骤：
  facts   核对画面上每个事实的来源（facts.py）
  crop    核对裁剪范围不截字、profile 与镜头代码一致、网格几何一致（check_crop.py）
  record  按 profile 重新录制终端素材（默认跳过，--record 才跑）
  render  渲染并体检（工程 tools/render.py）
  deliver 交付核对（工程 tools/deliver.py）

用法：
  python3 scripts/pipeline.py --profile video/profile
  python3 scripts/pipeline.py --profile video/profile --final
  python3 scripts/pipeline.py --profile video/profile --format all --final
  python3 scripts/pipeline.py --profile video/profile --only facts,crop
  python3 scripts/pipeline.py --profile video/profile --record --final
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import find_project, load_json, python_bin, resolve_profile  # noqa: E402

ALL_STEPS = ['facts', 'crop', 'record', 'sync', 'render', 'deliver']


class StepError(RuntimeError):
    pass


def run(cmd, cwd=None, label=''):
    """跑一步，失败即抛。"""
    print(f'\n── {label} ──', flush=True)
    t0 = time.time()
    r = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if r.returncode != 0:
        raise StepError(f'{label} 失败（退出码 {r.returncode}）')
    print(f'── {label} 完成，用时 {time.time() - t0:.1f}s ──', flush=True)


def step_facts(ctx):
    run([ctx['py'], ctx['kit'] / 'facts.py',
         '--profile', ctx['profile'], '--project', ctx['project']],
        label='事实核对')


def step_crop(ctx):
    run([ctx['py'], ctx['kit'] / 'check_crop.py',
         '--profile', ctx['profile'], '--project', ctx['project']],
        label='裁剪自检')


def step_record(ctx):
    """按 profile 的 capture 参数重录终端素材。"""
    profile = load_json(ctx['profile'])
    binary = (profile.get('binary') or {}).get('path')
    for name, asset in profile.get('assets', {}).items():
        cap = asset.get('capture', {})
        cmd = [ctx['py'], ctx['kit'] / 'record_terminal.py',
               '--name', name,
               '--cmd', ' '.join([str(binary)] + [str(c) for c in asset['command']]),
               '--project', ctx['project']]
        if asset.get('prompt'):
            cmd += ['--prompt', asset['prompt']]
        if asset.get('title'):
            cmd += ['--title', asset['title']]
        for flag, key in (('--cols', 'cols'), ('--rows', 'rows'), ('--fps', 'fps'),
                          ('--head', 'head'), ('--skip', 'skip'), ('--tail', 'tail'),
                          ('--out-width', 'out_width'), ('--seq-sec', 'seq_sec'),
                          ('--cps', 'cps'), ('--out-cps', 'out_cps'),
                          ('--line-max', 'line_max'), ('--gap', 'gap'), ('--hold', 'hold')):
            if cap.get(key) is not None:
                cmd += [flag, str(cap[key])]
        if cap.get('still'):
            cmd += ['--still']
        if cap.get('seq') is False:
            cmd += ['--no-seq']
        run(cmd, label=f'录制素材 {name}')


def step_sync(ctx):
    """重建时间线与 web/project.js。

    project.js 里的序列帧清单是扫描 web/img/*/ 得来的。重录素材后帧数变了，
    这份清单必须跟着更新，否则页面还在按旧清单加载图片（找不到文件就启动失败）。
    这一步会按配音重新对齐时间线，所以配音产物必须在。
    """
    run([ctx['py'], ctx['project'] / 'tools' / 'timeline.py'],
        cwd=ctx['project'], label='同步时间线与素材清单')


def step_render(ctx):
    cmd = [ctx['py'], ctx['project'] / 'tools' / 'render.py']
    if ctx['final']:
        cmd += ['--final']
    cmd += ['--format', ctx['format']]
    run(cmd, cwd=ctx['project'],
        label=f"渲染（{'正式档' if ctx['final'] else '草稿档'} · {ctx['format']}）")


def step_deliver(ctx):
    run([ctx['py'], ctx['project'] / 'tools' / 'deliver.py',
         '--format', ctx['format']], cwd=ctx['project'], label='交付核对')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default=None, help='profile 文件或目录')
    ap.add_argument('--project', default=None, help='视频工程目录')
    ap.add_argument('--format', default='all', help='画幅：all / 16x9 / 9x16 / 1x1')
    ap.add_argument('--final', action='store_true', help='正式档（默认草稿档）')
    ap.add_argument('--record', action='store_true', help='先按 profile 重录终端素材')
    ap.add_argument('--only', default=None, help='只跑这些步骤，逗号分隔')
    a = ap.parse_args()

    project = find_project(a.project)
    kit = Path(__file__).resolve().parent
    profile = resolve_profile(a.profile, project)

    steps = ALL_STEPS
    if a.only:
        steps = [s.strip() for s in a.only.split(',') if s.strip()]
        unknown = [s for s in steps if s not in ALL_STEPS]
        if unknown:
            sys.exit(f'未知步骤：{unknown}；可用：{ALL_STEPS}')

    ctx = {'project': project, 'kit': kit, 'profile': profile,
           'py': python_bin(project), 'final': a.final, 'format': a.format}

    print(f'视频流水线：{project}')
    print(f'  profile {profile} · 画幅 {a.format} · {"正式档" if a.final else "草稿档"}')
    print(f'  步骤：{" → ".join(steps)}')

    t0 = time.time()
    for s in ALL_STEPS:
        if s not in steps:
            continue
        if s == 'record' and not a.record:
            print('\n── 录制素材 ──\n   跳过（加 --record 重录）')
            continue
        {'facts': step_facts, 'crop': step_crop, 'record': step_record,
         'sync': step_sync, 'render': step_render, 'deliver': step_deliver}[s](ctx)

    print(f'\n✅ 流水线走完，用时 {time.time() - t0:.1f}s')
    if a.final:
        print(f'   成片在 {project}/out/ 下，交付核对在 {project}/out/交付核对.md')


if __name__ == '__main__':
    try:
        main()
    except StepError as e:
        print(f'\n❌ {e}\n   停在这一步，不继续渲染。', file=sys.stderr)
        sys.exit(1)
