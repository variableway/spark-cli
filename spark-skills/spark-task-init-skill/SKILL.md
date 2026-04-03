---
name: spark-task-init
description: Initialize spark task structure in any directory by running "spark task init"
type: skill
supported_agents:
  - claude-code
  - kimi
  - codex
  - opencode
---

# Spark Task Init Skill

This skill enables initializing spark task structure in any directory.

## Usage

When the user wants to initialize task structure in a directory, run:

```bash
spark task init
```

This will create:
- `tasks/features/` - Directory for feature files
- `tasks/config/` - Directory for configuration tasks
- `tasks/analysis/` - Directory for analysis tasks
- `tasks/mindstorm/` - Directory for brainstorming tasks
- `tasks/planning/` - Directory for planning tasks
- `tasks/prd/` - Directory for PRD documents
- `tasks/example-feature.md` - Example feature template

## Available Commands

After initialization, you can use:

```bash
# List all tasks and features
spark task list

# Create a new feature
spark task create my-feature

# Create with custom content
spark task create my-feature --content "Custom description"

# Delete a feature
spark task delete my-feature

# Delete without confirmation
spark task delete my-feature --force

# Implement a feature (requires kimi CLI)
spark task impl my-feature

# Show help
spark task --help
```

## Example Workflow

```bash
# 1. Initialize task structure
spark task init

# 2. Create a new feature
spark task create login-feature

# 3. List all features
spark task list

# 4. Implement the feature (if kimi CLI is installed)
spark task impl login-feature
```

## Requirements

- spark CLI must be installed
- For `spark task impl`: kimi CLI must be installed
- For GitHub workflow: github-task-workflow must be configured

## Notes

- If directories already exist, they will be preserved
- The example-feature.md serves as a template for new features
- Feature files are stored in `tasks/features/` directory
