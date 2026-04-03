#!/usr/bin/env python3
"""跨 Agent 的 GitHub Task Workflow 编排器。

用法：
    python orchestrate.py init tasks/login.md "使用 JWT 实现"
    python orchestrate.py status
    python orchestrate.py finish
    python orchestrate.py abort
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import get_github_token
from create_issue import create_issue, get_git_remote
from update_issue import update_issue, add_comment


STATE_FILE = Path(".github-task-workflow.state.json")


def _ensure_repo_and_token():
    repo = get_git_remote()
    token = get_github_token()
    if not repo:
        print("Error: Could not detect GitHub repository from git remote.", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("Error: GitHub token not found.", file=sys.stderr)
        print("Configure via GITHUB_TOKEN env var or .github-task-workflow.yaml", file=sys.stderr)
        sys.exit(1)
    return repo, token


def cmd_init(args):
    task_path = Path(args.task_file)
    if not task_path.exists():
        print(f"Error: Task file not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    repo, token = _ensure_repo_and_token()

    try:
        content = task_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading task file: {e}", file=sys.stderr)
        sys.stderr
        sys.exit(1)

    lines = content.split("\n")
    title = lines[0].lstrip("# ").strip() if lines else task_path.stem
    body = content

    if STATE_FILE.exists():
        old = json.loads(STATE_FILE.read_text())
        print(f"Warning: Existing workflow found for Issue #{old.get('issue')}. Abort it first if stale.", file=sys.stderr)

    try:
        issue = create_issue(repo, title, body, labels=["task"], token=token)
    except Exception as e:
        print(f"Error creating issue: {e}", file=sys.stderr)
        sys.exit(1)

    state = {
        "issue": issue["number"],
        "repo": repo,
        "task_file": str(task_path),
        "instructions": args.instructions or "",
        "html_url": issue.get("html_url", ""),
        "status": "created"
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))

    print(f"Created Issue #{issue['number']}: {issue.get('html_url', '')}")
    print(f"State saved to: {STATE_FILE}")
    print("\n=== NEXT STEP ===")
    print("Please implement the task now.")
    print("After implementation, run: python scripts/orchestrate.py finish")


def cmd_status(_args):
    if not STATE_FILE.exists():
        print("No active workflow found.")
        return

    state = json.loads(STATE_FILE.read_text())
    print(f"Active workflow:")
    print(f"  Issue:     #{state['issue']}")
    print(f"  URL:       {state.get('html_url', '')}")
    print(f"  Repo:      {state['repo']}")
    print(f"  Task file: {state['task_file']}")
    print(f"  Status:    {state['status']}")
    if state.get("instructions"):
        print(f"  Instructions: {state['instructions']}")


def cmd_finish(_args):
    if not STATE_FILE.exists():
        print("Error: No active workflow found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    state = json.loads(STATE_FILE.read_text())
    repo = state["repo"]
    issue_number = state["issue"]
    token = get_github_token()

    if not token:
        print("Error: GitHub token not found.", file=sys.stderr)
        sys.exit(1)

    # Gather git summary for the comment
    try:
        changed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, check=False
        ).stdout.strip()
    except Exception:
        changed = ""

    comment_lines = ["### Implementation Completed", ""]
    if state.get("instructions"):
        comment_lines.append(f"**Instructions**: {state['instructions']}")
        comment_lines.append("")
    if changed:
        comment_lines.append("**Files changed**:")
        for f in changed.split("\n"):
            if f.strip():
                comment_lines.append(f"- `{f}`")
    else:
        comment_lines.append("Task implementation is done.")

    comment = "\n".join(comment_lines)

    try:
        add_comment(repo, issue_number, comment, token=token)
        update_issue(repo, issue_number, state="closed", token=token)
        print(f"Updated and closed Issue #{issue_number}")
    except Exception as e:
        print(f"Error updating issue: {e}", file=sys.stderr)
        sys.exit(1)

    # Git commit and push
    try:
        subprocess.run(["git", "add", "-A"], check=False)
        subprocess.run(
            ["git", "commit", "-m", f"Complete task (Refs: #{issue_number})"],
            capture_output=True, text=True, check=False
        )
        push_result = subprocess.run(["git", "push"], capture_output=True, text=True, check=False)
        if push_result.returncode == 0:
            print("Code committed and pushed.")
        else:
            print("Commit created, but push may need attention.")
    except Exception as e:
        print(f"Git operation warning: {e}")

    STATE_FILE.unlink()
    print("Workflow complete.")


def cmd_abort(_args):
    if not STATE_FILE.exists():
        print("No active workflow to abort.")
        return

    state = json.loads(STATE_FILE.read_text())
    STATE_FILE.unlink()
    print(f"Aborted workflow for Issue #{state.get('issue')}")


def main():
    parser = argparse.ArgumentParser(description="GitHub Task Workflow Orchestrator")
    sub = parser.add_subparsers(dest="cmd", help="Available commands")

    p_init = sub.add_parser("init", help="Create issue from task file and save state")
    p_init.add_argument("task_file", help="Path to the task markdown file")
    p_init.add_argument("instructions", nargs="?", default="", help="Additional implementation instructions")

    sub.add_parser("status", help="Show active workflow state")
    sub.add_parser("finish", help="Update issue with summary, close it, and push code")
    sub.add_parser("abort", help="Remove active workflow state without updating issue")

    args = parser.parse_args()

    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "finish": cmd_finish,
        "abort": cmd_abort,
    }

    handler = handlers.get(args.cmd)
    if not handler:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
