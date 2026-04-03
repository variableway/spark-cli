#!/usr/bin/env python3
"""Watch tasks/ directory and auto-create GitHub issues for new .md files.

Usage:
    python task_watcher.py              # Watch ./tasks/
    python task_watcher.py --daemon     # Run in background
    python task_watcher.py --stop       # Stop background watcher
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None
    FileSystemEventHandler = object

# Allow importing sibling modules when run directly
sys.path.insert(0, str(Path(__file__).parent))
from create_issue import create_issue, get_git_remote
from config_loader import get_github_token


PID_FILE = Path(".task_watcher.pid")
PROCESSED_LOG = Path(".github-task-workflow.processed")


def load_processed() -> set:
    if not PROCESSED_LOG.exists():
        return set()
    return set(line.strip() for line in PROCESSED_LOG.read_text().split("\n") if line.strip())


def save_processed(filename: str):
    with open(PROCESSED_LOG, "a") as f:
        f.write(filename + "\n")


class TaskHandler(FileSystemEventHandler):
    def __init__(self, tasks_dir: Path, repo: str, token: str):
        self.tasks_dir = tasks_dir
        self.repo = repo
        self.token = token
        self.processed = load_processed()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix != ".md":
            return
        if path.name in self.processed:
            return

        print(f"[WATCHER] Detected new task: {path.name}")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WATCHER] Failed to read {path.name}: {e}")
            return

        title = content.split("\n")[0].lstrip("# ").strip() if content else path.name
        body = content

        try:
            issue = create_issue(self.repo, title, body, token=self.token)
            print(f"[WATCHER] Created issue #{issue['number']}: {issue['html_url']}")
            save_processed(path.name)
            self.processed.add(path.name)
        except Exception as e:
            print(f"[WATCHER] Error creating issue: {e}")


def run_watcher(tasks_dir: Path):
    if not HAS_WATCHDOG:
        print("Error: 'watchdog' package is required.")
        print("Install it with: pip install watchdog")
        sys.exit(1)

    tasks_dir.mkdir(exist_ok=True)

    repo = get_git_remote()
    if not repo:
        print("Error: Could not detect GitHub repository from git remote.")
        print("Please run this command inside a git repository with a GitHub remote.")
        sys.exit(1)

    token = get_github_token()
    if not token:
        print("Error: GitHub token not found.")
        print("Configure via GITHUB_TOKEN env var or config file.")
        sys.exit(1)

    observer = Observer()
    handler = TaskHandler(tasks_dir, repo, token)
    observer.schedule(handler, str(tasks_dir), recursive=False)
    observer.start()
    print(f"[WATCHER] Watching {tasks_dir.absolute()} for new .md tasks...")
    print(f"[WATCHER] Repository: {repo}")
    print("[WATCHER] Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WATCHER] Stopping...")
        observer.stop()
    observer.join()


def run_daemon(tasks_dir: Path):
    if PID_FILE.exists():
        print(f"Watcher already running (PID: {PID_FILE.read_text().strip()})")
        sys.exit(0)

    pid = os.fork()
    if pid > 0:
        PID_FILE.write_text(str(pid))
        print(f"[WATCHER] Started in background (PID: {pid})")
        return

    # Child process
    os.setsid()
    sys.stdout = open("task_watcher.log", "a")
    sys.stderr = sys.stdout
    run_watcher(tasks_dir)


def stop_daemon():
    if not PID_FILE.exists():
        print("No running watcher found.")
        return

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 15)
        print(f"[WATCHER] Stopped process {pid}")
    except ProcessLookupError:
        print(f"[WATCHER] Process {pid} not found, removing stale PID file.")
    PID_FILE.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Auto-create GitHub issues from new task files")
    parser.add_argument("--tasks-dir", default="tasks", help="Directory to watch (default: ./tasks)")
    parser.add_argument("--daemon", action="store_true", help="Run in background")
    parser.add_argument("--stop", action="store_true", help="Stop background watcher")
    args = parser.parse_args()

    tasks_dir = Path(args.tasks_dir)

    if args.stop:
        stop_daemon()
        return

    if args.daemon:
        run_daemon(tasks_dir)
    else:
        run_watcher(tasks_dir)


if __name__ == "__main__":
    main()
