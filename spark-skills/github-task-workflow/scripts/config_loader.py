#!/usr/bin/env python3
"""Configuration loader for GitHub Task Workflow skill.

Config priority (highest to lowest):
1. Command-line argument (--token)
2. Environment variable (GITHUB_TOKEN)
3. Project-level config (.github-task-workflow.yaml in current directory)
4. Global config (~/.config/github-task-workflow/config.yaml or ~/.github-task-workflow.yaml)
"""

import os
from pathlib import Path
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None


CONFIG_FILENAME = ".github-task-workflow.yaml"
GLOBAL_CONFIG_DIR = Path.home() / ".config" / "github-task-workflow"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.yaml"
LEGACY_GLOBAL_CONFIG = Path.home() / ".github-task-workflow.yaml"


def find_project_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find project-level config by walking up from start_dir.
    
    Args:
        start_dir: Directory to start searching from (default: current directory)
        
    Returns:
        Path to config file if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()
    
    current = start_dir.resolve()
    
    # Walk up directory tree looking for config file
    for parent in [current] + list(current.parents):
        config_file = parent / CONFIG_FILENAME
        if config_file.exists():
            return config_file
    
    return None


def find_global_config() -> Optional[Path]:
    """Find global config file.
    
    Returns:
        Path to config file if found, None otherwise
    """
    # Check XDG config location first
    if GLOBAL_CONFIG_FILE.exists():
        return GLOBAL_CONFIG_FILE
    
    # Check legacy location in home directory
    if LEGACY_GLOBAL_CONFIG.exists():
        return LEGACY_GLOBAL_CONFIG
    
    return None


def load_config_file(config_path: Path) -> dict:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        Configuration dictionary
    """
    if not HAS_YAML:
        # Fallback to simple parser for basic key: value format
        return _parse_simple_yaml(config_path)
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _parse_simple_yaml(path: Path) -> dict:
    """Parse simple YAML format without external dependency.
    
    Handles:
    - key: value
    - key:
        subkey: value
    """
    result = {}
    current_section = None
    
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith('#'):
                    continue
                
                # Check for section (key:)
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    
                    # Calculate indentation
                    indent = len(line) - len(line.lstrip())
                    
                    if indent == 0 and not val:
                        # New section
                        current_section = key
                        result[key] = {}
                    elif current_section and indent > 0:
                        # Subkey in current section
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]
                        result[current_section][key] = val
                    elif indent == 0:
                        # Top-level key with value
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]
                        result[key] = val
    except Exception:
        pass
    
    return result


def get_github_token(cli_token: Optional[str] = None) -> Optional[str]:
    """Get GitHub token using priority chain.
    
    Priority:
    1. CLI argument
    2. GITHUB_TOKEN environment variable
    3. Project-level config file
    4. Global config file
    
    Args:
        cli_token: Token from command-line argument
        
    Returns:
        GitHub token or None if not found
    """
    # Priority 1: CLI argument
    if cli_token:
        return cli_token
    
    # Priority 2: Environment variable
    env_token = os.environ.get("GITHUB_TOKEN")
    if env_token:
        return env_token
    
    # Priority 3: Project-level config
    project_config = find_project_config()
    if project_config:
        config = load_config_file(project_config)
        token = config.get("github", {}).get("token")
        if token:
            return token
    
    # Priority 4: Global config
    global_config = find_global_config()
    if global_config:
        config = load_config_file(global_config)
        token = config.get("github", {}).get("token")
        if token:
            return token
    
    return None


def get_config_info() -> dict:
    """Get information about current configuration sources.
    
    Returns:
        Dictionary with config file paths and token source
    """
    project_config = find_project_config()
    global_config = find_global_config()
    
    token_source = None
    if os.environ.get("GITHUB_TOKEN"):
        token_source = "environment"
    elif project_config:
        config = load_config_file(project_config)
        if config.get("github", {}).get("token"):
            token_source = "project"
    elif global_config:
        config = load_config_file(global_config)
        if config.get("github", {}).get("token"):
            token_source = "global"
    
    return {
        "project_config": str(project_config) if project_config else None,
        "global_config": str(global_config) if global_config else None,
        "token_source": token_source
    }


def init_global_config() -> Path:
    """Initialize global config directory and file.
    
    Returns:
        Path to created config file
    """
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config_file = GLOBAL_CONFIG_DIR / "config.yaml"
    if not config_file.exists():
        with open(config_file, 'w') as f:
            f.write("""# GitHub Task Workflow Configuration
# Place this file at ~/.config/github-task-workflow/config.yaml
# Or use project-level .github-task-workflow.yaml in your repo

github:
  # Your GitHub personal access token
  # Generate at: https://github.com/settings/tokens
  token: 

  # Default repository (optional, auto-detected from git if not set)
  # repo: owner/repo

# Default settings
# defaults:
#   labels:
#     - task
#   remote: origin
""")
    
    return config_file


def init_project_config(path: Optional[Path] = None) -> Path:
    """Initialize project-level config file.
    
    Args:
        path: Directory to create config in (default: current directory)
        
    Returns:
        Path to created config file
    """
    if path is None:
        path = Path.cwd()
    
    config_file = path / CONFIG_FILENAME
    
    with open(config_file, 'w') as f:
        f.write("""# GitHub Task Workflow - Project Configuration
# This config is specific to this project

github:
  # GitHub token (or use GITHUB_TOKEN env var)
  token: 

  # Repository for this project (auto-detected from git if not set)
  # repo: owner/repo

# Task templates (optional)
# templates:
#   default: |
#     ## Description
#     {description}
#     
#     ## Acceptance Criteria
#     - [ ] Criteria 1
""")
    
    return config_file


def main():
    """CLI for config management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Task Workflow Config Manager")
    parser.add_argument("--init-global", action="store_true", help="Initialize global config")
    parser.add_argument("--init-project", action="store_true", help="Initialize project config")
    parser.add_argument("--show-sources", action="store_true", help="Show config sources")
    
    args = parser.parse_args()
    
    if args.init_global:
        config_path = init_global_config()
        print(f"Created global config: {config_path}")
        print("Edit this file to add your GitHub token.")
        return
    
    if args.init_project:
        config_path = init_project_config()
        print(f"Created project config: {config_path}")
        print("Edit this file to add your GitHub token.")
        return
    
    if args.show_sources:
        info = get_config_info()
        print("Configuration sources:")
        print(f"  Project config: {info['project_config'] or 'Not found'}")
        print(f"  Global config:  {info['global_config'] or 'Not found'}")
        print(f"  Token source:   {info['token_source'] or 'Not configured'}")
        return
    
    parser.print_help()


if __name__ == "__main__":
    main()
