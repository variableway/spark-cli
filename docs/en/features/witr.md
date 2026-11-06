# Process Diagnostics

## Overview

`spark witr` (Why Is This Running) answers the question "why is this process or port running?". It does more than report a PID — it lays out the whole story: who started it, which service manager supervises it, which container it runs in, which ports it listens on, and which files it holds open.

Answering these questions usually means switching back and forth between `ps`, `lsof`, `docker ps`, `systemctl` and launchd, then stitching the output together by hand. witr merges those sources into a single lookup and adds risk findings along the way, such as a process running as root, a suspicious working directory, a public interface bind, or `LD_PRELOAD` in the environment.

## Core Capabilities

### Ancestry Chain and Source Detection

witr walks up the parent chain from the target process and lists who started whom. The head of that chain is then identified as a concrete source type:

| Source type | Description |
|------------|-------------|
| `container` | The process was started by a container runtime |
| `systemd` | Managed by a systemd unit |
| `launchd` | Managed by a launchd service (macOS) |
| `bsdrc` | Started by a BSD rc script |
| `supervisor` | Started by a process manager such as supervisor |
| `cron` | Started by a scheduled job |
| `ssh` | Started from an SSH session |
| `shell` | Started from an interactive shell |
| `windows_service` | Started as a Windows service |
| `init` | Started by the system init process |

When no known source is recognized, the source is marked `unknown` and reported as the warning "No known supervisor or service manager detected".

### Collected Data

A single lookup covers these categories of information:

- **Process**: PID, PPID, command, full command line, executable path, start time, running user, working directory, owning Git repository and branch, container, service name, health status, and whether it was forked
- **Network**: every socket the process owns (protocol and state, such as `LISTEN`, `ESTABLISHED`, `CLOSE_WAIT`, `TIME_WAIT`). A port lookup additionally explains the socket state of that port and suggests a workaround, for example `TIME_WAIT` is explained as "Wait ~60s for the OS to release it, or enable SO_REUSEADDR in your code."
- **Container**: container runtime, ID, name, image, command, state, creation and start times, networks, mounts, port mappings, and the compose project and service names
- **Environment variables**: the environment variable list of the process (`--env`)
- **Extended information** (`--verbose`): memory breakdown, I/O statistics, file descriptor list, file descriptor count and limit, child processes, thread count; on macOS also energy impact, whether it prevents system sleep, thermal state, CPU and memory usage
- **File context**: number of open files, file descriptor limit, file locks held by the process, and watched directories

### Risk Findings

witr summarizes suspicious findings into a warning list:

- The process or an ancestor restarted more than 5 times
- A zombie process (`zombie`), a stopped process (`stopped`), high CPU, high memory
- Listening on a public interface (`0.0.0.0` or `::`)
- Running as root, or holding dangerous capabilities (such as `CAP_SYS_ADMIN`, `CAP_SYS_PTRACE`)
- Running for more than 90 days
- A suspicious working directory (`/`, `/tmp`, `/var/tmp`)
- Running from a deleted executable
- A container without a healthcheck (a best-effort check, snap and flatpak excluded)
- The service name and the process name do not match
- Suspicious environment variables: library injection in the form of `LD_PRELOAD` or `DYLD_*`

### Lookup Targets

Besides passing a process name directly, witr supports four flag-based lookup modes:

| Target | Flag | Description |
|--------|------|-------------|
| Process name | positional argument | Matches the process name and command line by substring by default; `--exact` switches to exact matching of whole command-line tokens |
| PID | `--pid` | Looks up a PID directly, which must be a positive integer |
| Port | `--port` | Finds the process listening on a port, which must be between 1 and 65535 |
| File | `--file` | Finds the process holding a file open, not supported on Windows |
| Container | `--container` | Matches containers by name, image or command, covering docker, podman, nerdctl, crictl and jail |

Different target kinds can be mixed in one command, and multiple targets are processed in command-line order.

### Machine-Readable Output

`--json` turns the result into JSON for scripting: a single target produces an object, multiple targets produce an array, and failed lookups are merged into the array as `{"Target": ..., "Error": ...}` entries. Combined with `--short`, `--tree`, `--warnings` or `--env`, the JSON structure narrows down to only the fields that view needs.

### Typical Scenarios

- A port is taken and the service will not start: `spark witr --port 8080` shows who holds the port and who started it
- A background process of unknown origin: `spark witr node --tree` expands the whole parent chain
- Container troubleshooting: `spark witr --container redis` returns the image, port mappings and compose ownership
- A file lock conflict: `spark witr --file /var/lib/dpkg/lock` locates the lock holder
- Checking a process environment: `spark witr --pid 1234 --env`
- Wiring into an automated pipeline: `spark witr --port 8080 --json`, then hand it to `jq` or another script

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--pid` | strings | | Look up by PID, repeatable |
| `--port` | strings | | Look up by port, repeatable |
| `--file` | strings | | Look up by open file, repeatable |
| `--container` | strings | | Look up by container, repeatable |
| `--json` | bool | `false` | Output machine-readable JSON |

See the command spec page for the complete flag list.

## Related Docs

- [Witr Command Spec](../spec/witr.md)
- [Witr Usage Guide](../usage/witr.md)
