"""定位视频工程、profile、仓库根与 python 解释器。

同一份脚本既放在 Skill 的 scripts/ 下，也放在工程的 kit/ 下，两种位置都要能找到工程。
查找顺序（先到先得）：

工程目录（里面要有 project.json 和 web/）：
  1. 命令行给的 --project
  2. 环境变量 VIDEO_PROJECT
  3. 脚本所在位置的同级与上级（找 project/ 或含 web/ 的目录）
  4. 当前工作目录往上找 4 层

profile（--profile 可以给文件，也可以给目录）：
  1. 给的是文件 → 就用它
  2. 给的是目录 → 目录里除 facts.json 外的 *.json
  3. 没给 → 工程目录同级的 profile/
"""
import json
import os
import sys
from pathlib import Path

FACTS_NAME = 'facts.json'


def _looks_like_project(d: Path) -> bool:
    return (d / 'project.json').is_file() and (d / 'web').is_dir()


def find_project(explicit=None, required=True):
    """返回视频工程目录（里面有 project.json 和 web/）。找不到就报错退出。"""
    cands = []
    if explicit:
        cands.append(Path(explicit).expanduser())
    env = os.environ.get('VIDEO_PROJECT')
    if env:
        cands.append(Path(env).expanduser())

    here = Path(__file__).resolve().parent
    cands += [here.parent / 'project', here.parent, here.parent.parent / 'project']

    cwd = Path.cwd().resolve()
    for p in [cwd] + list(cwd.parents)[:4]:
        cands += [p / 'project', p]

    for c in cands:
        c = c.resolve()
        if _looks_like_project(c):
            return c

    if required:
        raise SystemExit(
            '找不到视频工程目录（需要同时有 project.json 和 web/）。\n'
            '用 --project 指定，或设环境变量 VIDEO_PROJECT。'
        )
    return None


def resolve_profile(explicit=None, project=None):
    """返回 profile 配置文件（*.json）的路径。

    explicit 可以是文件，也可以是目录；目录里除 facts.json 外的 *.json 都算候选。
    拿不准时取字典序第一个，并在报错信息里把所有候选列出来。
    """
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p.resolve()
        if p.is_dir():
            cands = sorted(c for c in p.glob('*.json') if c.name != FACTS_NAME)
            if not cands:
                raise SystemExit(f'{p} 里没有 profile 文件（除 {FACTS_NAME} 外的 *.json）')
            if len(cands) > 1:
                print(f'[profile] {p} 里有多个候选，取第一个：{cands[0].name}',
                      file=sys.stderr)
            return cands[0].resolve()
        raise SystemExit(f'找不到 profile：{p}')

    if project is None:
        project = find_project(required=False)
    if project is None:
        raise SystemExit('找不到视频工程目录，用 --project 指定，或设 VIDEO_PROJECT。')

    prof_dir = project.parent / 'profile'
    if not prof_dir.is_dir():
        raise SystemExit(f'找不到 profile 目录：{prof_dir}')
    cands = sorted(c for c in prof_dir.glob('*.json') if c.name != FACTS_NAME)
    if not cands:
        raise SystemExit(f'{prof_dir} 里没有 profile 文件')
    return cands[0].resolve()


def facts_path(profile_file, explicit=None):
    """facts.json 的路径：显式指定优先，否则取 profile 同目录下的 facts.json。"""
    if explicit:
        return Path(explicit).expanduser().resolve()
    p = Path(profile_file).resolve().parent / FACTS_NAME
    if not p.is_file():
        raise SystemExit(f'找不到事实清单：{p}')
    return p


def find_repo_root(start):
    """找 git 仓库根（profile 里的 cwd:"repo" 指的就是它）。找不到就返回 start。"""
    start = Path(start).resolve()
    for d in [start] + list(start.parents):
        if (d / '.git').exists():
            return d
    return start


def python_bin(project):
    """优先用工程自己的 .venv 里的 python，其次系统 python。"""
    venv = Path(project) / '.venv' / 'bin' / 'python'
    return str(venv) if venv.exists() else sys.executable


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2),
                           encoding='utf-8')
