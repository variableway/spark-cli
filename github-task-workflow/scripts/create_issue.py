#!/usr/bin/env python3
"""Create a GitHub issue from a task description."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def create_issue(repo: str, title: str, body: str, labels: list = None, token: str = None) -> dict:
    """Create a GitHub issue via API.
    
    Args:
        repo: Repository in format "owner/repo"
        title: Issue title
        body: Issue body (markdown supported)
        labels: Optional list of label names
        token: GitHub personal access token
        
    Returns:
        Created issue data as dict
    """
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN env var or pass --token.")
    
    url = f"https://api.github.com/repos/{repo}/issues"
    
    data = {
        "title": title,
        "body": body
    }
    
    if labels:
        data["labels"] = labels
    
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
    parser = argparse.ArgumentParser(description="Create a GitHub issue from a task")
    parser.add_argument("--repo", required=True, help="Repository (owner/repo)")
    parser.add_argument("--title", required=True, help="Issue title")
    parser.add_argument("--body", required=True, help="Issue body (markdown)")
    parser.add_argument("--labels", help="Comma-separated list of labels")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--output-json", action="store_true", help="Output full JSON response")
    
    args = parser.parse_args()
    
    labels = None
    if args.labels:
        labels = [l.strip() for l in args.labels.split(",")]
    
    try:
        issue = create_issue(args.repo, args.title, args.body, labels, args.token)
        
        if args.output_json:
            print(json.dumps(issue, indent=2))
        else:
            print(f"Issue created: {issue['number']}")
            print(f"URL: {issue['html_url']}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
