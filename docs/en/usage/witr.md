# spark witr — Process Diagnostics

Investigate why a process or port is running, tracing the process ancestor chain. witr (Why Is This Running) is a process diagnostics tool built into Spark.

## Quick Reference

```bash
spark witr nginx                              # Look up by process name
spark witr --pid 1234                         # Look up by PID
spark witr --port 8080                        # Find the process bound to a port
spark witr --file /var/lib/dpkg/lock          # Find the process holding a file open
spark witr --container redis                  # Inspect a container
spark witr nginx --tree                       # Show the process tree
spark witr nginx --env                        # Show environment variables
spark witr nginx --json                       # JSON output
spark witr nginx --short                      # Single-line output
spark witr nginx --warnings                   # Show warnings only
spark witr nginx --verbose                    # Extended information
spark witr --port 8080 --env --json           # Combined flags
```

---

## Basic Usage

### By name

```bash
spark witr nginx
spark witr nginx --exact                      # Exact match (no fuzzy search)
```

### By PID

```bash
spark witr --pid 1234
spark witr --pid 1234,5678                    # Multiple PIDs
```

### By port

```bash
spark witr --port 8080
spark witr --port 8080,3000                   # Multiple ports
```

### By file

```bash
spark witr --file /var/lib/dpkg/lock
```

### By container

```bash
spark witr --container redis
```

---

## Output Modes

| Flag | Short | Description |
|------|-------|-------------|
| `--tree` | `-t` | Show only the process ancestor tree |
| `--short` | `-s` | Compact single-line output |
| `--env` | | Show process environment variables |
| `--verbose` | | Show extended information (memory, I/O, file descriptors) |
| `--warnings` | | Show only warnings (suspicious env, args, parent) |
| `--json` | | JSON output |
| `--no-color` | | Disable colors (for CI or piping) |

---

## Mixed Queries

You can query multiple targets at once:

```bash
spark witr nginx node                         # Multiple process names
spark witr --port 8080 --port 3000            # Multiple ports
spark witr --pid 1234 --pid 5678              # Multiple PIDs
spark witr nginx --pid 1234 --port 8080       # Mixed query
```

---

## Interactive Mode

With no arguments, or when only interactive flags are passed, the TUI is launched:

```bash
spark witr                                    # Launch the interactive TUI
spark witr --interactive                      # Explicit TUI
spark witr -i                                 # Short flag
```

## Related

- [System Utilities](./magic)
- [Git Management](./git)
