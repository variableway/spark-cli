# Script Management

## Overview

`spark script` manages and executes custom automation scripts. Scripts can be declared in the config file or live as executable files in the `scripts/` directory.

## Core Capabilities

### Script Discovery

Automatically discover scripts from two sources:

1. **Config-file scripts**: the `spark.scripts` (or top-level `scripts`) key in `~/.spark.yaml`.
2. **Directory scripts**: executable files under the project's `scripts/` directory.

Config-file scripts take precedence.

```bash
spark script list
```

### Script Execution

Run a registered script by name, with optional additional arguments.

```bash
spark script run my-script
spark script run deploy -- --env production
```

## Parameters

| Command | Argument | Description |
|---------|----------|-------------|
| `list` | — | List every available script |
| `run` | `<name> [args...]` | Run the script and forward arguments |

## Config Example

```yaml
# ~/.spark.yaml
spark:
  scripts:
    - name: hello
      description: Say hello
      command: echo "Hello, World!"
```

## Related

- [Script Command Spec](/en/spec/script)
