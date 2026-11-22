#!/usr/bin/env python3
"""事实核对：画面上出现的每个事实，回到它的来源去比对。

为什么要有这个：片子里写着「v0.4.0」「十个命令族」「make build → ~/.local/bin/spark」，
观众会当真。自动体检量不了这件事——它看画面，不看数字对不对。
所以把每个事实写成一条可执行的检查（跑什么命令、读哪个文件、必须包含哪几串），
渲染前跑一遍：编造的事实在这里就被拦住，不用等到成片才发现。

检查类型（写在 facts.json 每条事实的 check 里）：
  command         跑一条命令，输出里必须包含 expect_all 的每一串
                  binary:false 表示这条不是被介绍工具的子命令，不要拼二进制
                  cwd:"repo" 表示在仓库根目录跑
  file            读仓库里的一个文件，内容必须包含 expect 的每一串
  quick_commands  profile.quick_commands 里的每条子命令都得存在（逐条跑 --help）
  manual          机器核不了，必须人工确认；reason 里写清为什么核不了

用法：
  python3 scripts/facts.py --profile video/profile
  python3 scripts/facts.py --profile video/profile/spark-cli.json --only version,site_url
  python3 scripts/facts.py --profile video/profile --repo-root . --json

退出码：0 全部通过（manual 项不算失败）；1 有事实对不上；2 有事实核不了（缺二进制等）。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (  # noqa: E402
    facts_path, find_project, find_repo_root, load_json, resolve_profile,
)

OK, BAD, SKIP, MANUAL = '✅', '❌', '⚠️', '📝'


def run_cmd(cmd, cwd=None, binary=None):
    """跑命令，返回 (stdout+stderr, returncode)。

    binary 给了就把它放在命令前面（跑被介绍工具的子命令）；
    要跑的是别的工具（git、ls）就别传 binary，或在 check 里写 "binary": false。
    """
    exe = [str(binary)] if binary else []
    try:
        r = subprocess.run(exe + [str(c) for c in cmd], cwd=cwd,
                           capture_output=True, text=True, timeout=120)
        return (r.stdout or '') + (r.stderr or ''), r.returncode
    except (OSError, subprocess.TimeoutExpired) as e:
        return f'(执行失败: {e})', 127


def resolve_binary(profile, repo_root):
    """找出被介绍工具的可执行文件路径。找不到返回 None。"""
    raw = (profile.get('binary') or {}).get('path')
    if not raw:
        return None
    p = Path(str(raw)).expanduser()
    if not p.is_absolute():
        p = repo_root / p
    return str(p) if p.exists() else None


def check_one(fact, profile, repo_root, binary):
    """核对一条事实，返回 (状态, 说明)。"""
    c = fact.get('check', {})
    kind = c.get('type')

    if kind == 'manual':
        return MANUAL, c.get('reason', '需人工确认')

    if kind == 'command':
        use_bin = c.get('binary', True) and binary
        out, rc = run_cmd(c.get('command', []),
                          cwd=repo_root if c.get('cwd') == 'repo' else None,
                          binary=binary if use_bin else None)
        if rc == 127 and '(执行失败' in out:
            return SKIP, out
        missing = [s for s in c.get('expect_all', []) if s not in out]
        if missing:
            return BAD, f'输出里没有：{missing}'
        return OK, f'{len(c.get("expect_all", []))} 段都匹配'

    if kind == 'file':
        f = repo_root / c.get('path', '')
        if not f.exists():
            return SKIP, f'文件不存在：{c.get("path")}'
        text = f.read_text(encoding='utf-8', errors='replace')
        missing = [s for s in c.get('expect', c.get('expect_all', [])) if s not in text]
        if missing:
            return BAD, f'{c.get("path")} 里没有：{missing}'
        return OK, f'{c.get("path")} 匹配'

    if kind == 'quick_commands':
        missing = []
        for qc in profile.get('quick_commands', []):
            out, rc = run_cmd(list(qc) + ['--help'], binary=binary)
            if rc != 0:
                missing.append(' '.join(qc))
        if missing:
            return BAD, f'这些子命令不存在：{missing}'
        return OK, f'{len(profile.get("quick_commands", []))} 条子命令都存在'

    return SKIP, f'未知的检查类型：{kind}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default=None, help='profile 文件或目录')
    ap.add_argument('--facts', default=None, help='事实清单，默认取 profile 同目录的 facts.json')
    ap.add_argument('--project', default=None, help='视频工程目录，默认自动找')
    ap.add_argument('--repo-root', default=None, help='仓库根，默认从 profile 位置往上找 .git')
    ap.add_argument('--only', default=None, help='只核对这些 id，逗号分隔')
    ap.add_argument('--json', action='store_true', help='输出 JSON')
    a = ap.parse_args()

    project = find_project(a.project, required=False)
    profile_file = resolve_profile(a.profile, project)
    profile = load_json(profile_file)

    facts_file = facts_path(profile_file, a.facts)
    facts_doc = load_json(facts_file)
    facts = facts_doc.get('facts', [])

    repo_root = Path(a.repo_root).resolve() if a.repo_root else find_repo_root(profile_file.parent)
    binary = resolve_binary(profile, repo_root)

    only = set(a.only.split(',')) if a.only else None
    results = []
    for fact in facts:
        if only and fact.get('id') not in only:
            continue
        status, detail = check_one(fact, profile, repo_root, binary)
        results.append({'id': fact.get('id'), 'on_screen': fact.get('on_screen'),
                        'where': fact.get('where'), 'status': status, 'detail': detail})

    if not results:
        sys.exit('没有可核对的事实（--only 过滤后为空？）')

    bad = [r for r in results if r['status'] == BAD]
    skipped = [r for r in results if r['status'] == SKIP]
    manual = [r for r in results if r['status'] == MANUAL]
    ok = [r for r in results if r['status'] == OK]

    if a.json:
        print(json.dumps({'results': results, 'ok': len(ok), 'bad': len(bad),
                          'skipped': len(skipped), 'manual': len(manual)},
                         ensure_ascii=False, indent=2))
    else:
        print(f'事实核对：{profile.get("name")}（仓库根 {repo_root}）')
        if not binary:
            print(f'  {SKIP} 找不到二进制 {(profile.get("binary") or {}).get("path")}，'
                  f'依赖命令输出的事实都核不了；先按 profile.binary.build 构建')
        for r in results:
            print(f'  {r["status"]} {r["id"]:<18} {r["detail"]}')
            if r['status'] in (BAD, MANUAL):
                print(f'      画面上：{r["on_screen"]}（{r["where"]}）')
        print(f'\n通过 {len(ok)} · 不符 {len(bad)} · 核不了 {len(skipped)} · 需人工 {len(manual)}')

    if bad:
        print('\n有事实和来源对不上，先改画面或改事实来源，不要带着它渲染。')
        sys.exit(1)
    if skipped and not binary:
        print('\n警告：有事实没能核（缺二进制），渲染前请先构建。')
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
