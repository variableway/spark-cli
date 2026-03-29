#!/usr/bin/env python3
"""Update a GitHub issue with implementation details."""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error

from config_loader import get_github_token, get_config_info


def get_git_remote(repo_url: str = None, remote_name: str = "origin") -> str:
    """Get owner/repo from git remote or provided URL.
    
    Args:
        repo_url: Optional repo URL or owner/repo string
        remote_name: Git remote name to check (default: origin)
        
    Returns:
        owner/repo string
    """
    if repo_url:
        # Check if already in owner/repo format
        if re.match(r"^[\w.-]+/[\w.-]+$", repo_url):
            return repo_url
        # Extract from GitHub URL
        match = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", repo_url)
        if match:
            return match.group(1)
    
    # Try to get from git config
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        match = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", remote_url)
        if match:
            return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return None


def update_issue(repo: str, issue_number: int, body: str = None, state: str = None, token: str = None) -> dict:
    """Update a GitHub issue via API.
    
    Args:
        repo: Repository in format "owner/repo"
        issue_number: Issue number
        body: New body content (appended to existing if using --append)
        state: New state ("open" or "closed")
        token: GitHub personal access token (or loaded from config)
        
    Returns:
        Updated issue data as dict
    """
    if not token:
        raise ValueError(
            "GitHub token required. Provide via:\n"
            "  1. --token argument\n"
            "  2. GITHUB_TOKEN environment variable\n"
            "  3. Project config: .github-task-workflow.yaml\n"
            "  4. Global config: ~/.config/github-task-workflow/config.yaml"
        )
    
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    
    data = {}
    if body:
        data["body"] = body
    if state:
        data["state"] = state
    
    if not data:
        raise ValueError("No updates specified. Provide --body or --state.")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="PATCH"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"GitHub API error: {e.code} - {error_body}")


def get_issue(repo: str, issue_number: int, token: str = None) -> dict:
    """Get current issue data."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"GitHub API error: {e.code} - {error_body}")


def add_comment(repo: str, issue_number: int, body: str, token: str = None) -> dict:
    """Add a comment to an issue."""
    if not token:
        raise ValueError(
            "GitHub token required. Provide via:\n"
            "  1. --token argument\n"
            "  2. GITHUB_TOKEN environment variable\n"
            "  3. Project config: .github-task-workflow.yaml\n"
            "  4. Global config: ~/.config/github-task-workflow/config.yaml"
        )
    
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    
    data = {"body": body}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"GitHub API error: {e.code} - {error_body}")


def main():
    parser = argparse.ArgumentParser(
        description="Update a GitHub issue with implementation details",
        epilog="If --repo is not provided, will try to detect from git remote."
    )
    parser.add_argument("--repo", help="Repository (owner/repo or URL). Auto-detected from git if not provided.")
    parser.add_argument("--remote", default="origin", help="Git remote name to use for auto-detection (default: origin)")
    parser.add_argument("--issue", type=int, required=True, help="Issue number")
    parser.add_argument("--body", help="New body content")
    parser.add_argument("--append", action="store_true", help="Append to existing body")
    parser.add_argument("--comment", help="Add as comment instead of editing body")
    parser.add_argument("--state", choices=["open", "closed"], help="Update issue state")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--output-json", action="store_true", help="Output full JSON response")
    
    args = parser.parse_args()
    
    # Detect repo
    repo = get_git_remote(args.repo, args.remote)
    if not repo:
        print("Error: Could not detect repository.", file=sys.stderr)
        print("Please provide --repo or run from within a git repository with GitHub remote.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Using repository: {repo}")
    
    # Get token using priority chain
    token = get_github_token(args.token)
    if not token:
        print("Error: GitHub token not found.", file=sys.stderr)
        print("\nTo configure:", file=sys.stderr)
        print("  1. Set GITHUB_TOKEN environment variable", file=sys.stderr)
        print("  2. Create project config: .github-task-workflow.yaml", file=sys.stderr)
        print("  3. Create global config: ~/.config/github-task-workflow/config.yaml", file=sys.stderr)
        print("\nOr run: python scripts/config_loader.py --init-global", file=sys.stderr)
        sys.exit(1)
    
    # Show token source (without revealing the token)
    config_info = get_config_info()
    if config_info["token_source"]:
        print(f"Using token from: {config_info['token_source']}")
    
    try:
        # If appending, get current body first
        if args.append and args.body:
            current = get_issue(repo, args.issue, token)
            new_body = current["body"] + "\n\n---\n\n" + args.body
        else:
            new_body = args.body
        
        # Add comment if specified
        if args.comment:
            comment = add_comment(repo, args.issue, args.comment, token)
            print(f"Comment added: {comment['html_url']}")
        
        # Update issue body/state if specified
        if new_body or args.state:
            issue = update_issue(repo, args.issue, new_body, args.state, token)
            
            if args.output_json:
                print(json.dumps(issue, indent=2))
            else:
                print(f"Issue #{issue['number']} updated")
                print(f"URL: {issue['html_url']}")
                if args.state:
                    print(f"State: {issue['state']}")
                    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
