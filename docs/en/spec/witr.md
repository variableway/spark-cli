# spark witr — Command Spec

Process diagnostics command. Explains why a process or port is running by tracing its ancestor chain.

## Parent

```
spark witr
```

No arguments, no flags. Running `spark witr` on its own launches the interactive TUI.

---

## spark witr

```
spark witr [process name...] [flags]
```

| Flag | Short | Type | Default | Required | Description |
|------|-------|------|---------|----------|-------------|
| `--container` | `-c` | strings | | No | Container name to look up, repeatable |
| `--env` | | bool | `false` | No | Show environment variables for the process |
| `--exact` | `-x` | bool | `false` | No | Use exact name matching (no substring search) |
| `--file` | `-f` | strings | | No | File path held open by a process, repeatable |
| `--help` | `-h` | bool | `false` | No | Show help |
| `--interactive` | `-i` | bool | `false` | No | Interactive mode (TUI) |
| `--json` | | bool | `false` | No | Show result as JSON |
| `--no-color` | | bool | `false` | No | Disable colorized output |
| `--pid` | | strings | | No | PID to look up, repeatable |
| `--port` | `-o` | strings | | No | Port to look up, repeatable |
| `--short` | `-s` | bool | `false` | No | Show only ancestry |
| `--tree` | `-t` | bool | `false` | No | Show only ancestry as a tree |
| `--verbose` | | bool | `false` | No | Show extended process information |
| `--version` | `-v` | bool | `false` | No | Show the witr version |
| `--warnings` | | bool | `false` | No | Show only warnings |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `process name` | string[] | No | Process name to look up, multiple values allowed |

`--pid`, `--port`, `--file` and `--container` are repeatable string-slice flags. Either repeat the flag or pass comma-separated values:

```bash
spark witr --port 8080 --port 3000
spark witr --pid 1234,5678
```

Lookup targets are processed in the order they appear on the command line, and different target kinds can be mixed:

```bash
spark witr nginx --pid 1234 --port 8080
```

`--file` is not supported on Windows and returns `finding process by file is not supported on Windows`.

### TUI Trigger Rule

The interactive TUI opens instead of printing text results when either of these holds:

- `--interactive` / `-i` is passed explicitly
- No lookup target is given at all: no `--pid`, `--port`, `--file` or `--container`, no `--env`, and no positional argument

Display-only flags such as `--json`, `--tree` or `--short` still enter the TUI, because they do not constitute a lookup target.

Passing only `--env` without any target does not enter the TUI; the command fails with:

```
must specify --pid, --port, --file, --container, or a process name
```

### Output Formats

The default text output prints these fields in order: `Target`, `Process`, `User`, `Container`, `Service`, `Command`, `Started`, `Why It Exists` (the ancestor chain), `Source`, `Description`, `Sockets`, `Warnings`.

`--short` prints only the ancestor chain on a single line, joining processes with `→`:

```
launchd (pid 1)
```

`--tree` prints only the tree, rooted at the target process with its children below it:

```
launchd (pid 1)
  ├─ /usr/libexec/logd (pid 341)
  ├─ /usr/libexec/smd (pid 342)
```

`--warnings` prints only the process information and the warning list.

`--env` prints only the process information and the environment variables.

`--json` prints machine-readable JSON. A single target produces one object; multiple targets produce a JSON array, and failed lookups are included in the array as `{"Target": ..., "Error": ...}` entries. The JSON shape follows the display flags:

| Combination | JSON structure |
|------|------|
| `--json` | Full result object: `Target`, `ResolvedTarget`, `Process`, `RestartCount`, `Ancestry`, `Source`, `Warnings`, plus `Children`, `SocketInfo`, `ResourceContext` and `FileContext` when present |
| `--json --short` | Ancestry array whose elements are `{"PID": ..., "Command": ...}` |
| `--json --tree` | `{"Ancestry": [...], "Children": [...]}` whose elements are `{"PID": ..., "Command": ...}` |
| `--json --warnings` | `{"PID": ..., "Process": ..., "Command": ..., "Warnings": [...]}` |
| `--json --env` | `{"PID": ..., "Process": ..., "Command": ..., "Env": [...]}` |

The `Target` object carries the fields `Type` and `Value`, where `Type` is one of `name`, `pid`, `port`, `file`, `container`.

`--env` has the highest priority: once it is set, only the environment variables are printed and the other display flags are ignored.

`--no-color` turns off colorized output, which suits CI and piped output.

### Exit Codes

| Exit code | Meaning |
|------|------|
| `0` | The lookup succeeded and there are no warnings |
| `1` | There are warnings, or an internal error occurred |
| `2` | No matching process was found |
| `3` | Insufficient permissions, for example the port exists but the owning process cannot be identified |
| `4` | Invalid input, for example no lookup target at all, or several processes matched |

With multiple targets, the highest exit code among all targets is returned.

When a name matches several processes, the command lists the candidates and suggests re-running with `--pid`:

```
Multiple matching processes found:

[1] nginx (pid 1234)
    /usr/sbin/nginx -g daemon on; master_process on;

Re-run with:
  witr --pid <pid>
```

### Related Docs

- [Witr Usage Guide](../usage/witr.md)
- [Witr Capabilities](../features/witr.md)
