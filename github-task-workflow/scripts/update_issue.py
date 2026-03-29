#!/usr/bin/env python3
"""Update a GitHub issue with implementation details."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def update_issue(repo: str, issue_number: int, body: str = None, state: str = None, token: str = None) -> dict:
    """Update a GitHub issue via API.
    
    Args:
        repo: Repository in format "owner/repo"
        issue_number: Issue number
        body: New body content (appended to existing if using --append)
        state: New state ("open" or "closed")
        token: GitHub personal access token
        
    Returns:
        Updated issue data as dict
    """
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN env var or pass --token.")
    
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
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    
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
        token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN env var or pass --token.")
    
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
    parser = argparse.ArgumentParser(description="Update a GitHub issue with implementation details")
    parser.add_argument("--repo", required=True, help="Repository (owner/repo)")
    parser.add_argument("--issue", type=int, required=True, help="Issue number")
    parser.add_argument("--body", help="New body content")
    parser.add_argument("--append", action="store_true", help="Append to existing body")
    parser.add_argument("--comment", help="Add as comment instead of editing body")
    parser.add_argument("--state", choices=["open", "closed"], help="Update issue state")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--output-json", action="store_true", help="Output full JSON response")
    
    args = parser.parse_args()
    
    try:
        # If appending, get current body first
        if args.append and args.body:
            current = get_issue(args.repo, args.issue, args.token)
            new_body = current["body"] + "\n\n---\n\n" + args.body
        else:
            new_body = args.body
        
        # Add comment if specified
        if args.comment:
            comment = add_comment(args.repo, args.issue, args.comment, args.token)
            print(f"Comment added: {comment['html_url']}")
        
        # Update issue body/state if specified
        if new_body or args.state:
            issue = update_issue(args.repo, args.issue, new_body, args.state, args.token)
            
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
