# Quick Start

## Install

```bash
git clone https://github.com/variableway/spark-cli.git
cd spark-cli
make build
```

`make build` compiles the binary and installs it to `~/.local/bin/spark`. Make sure that directory is on your `$PATH`.

## Configure

Create `~/.spark.yaml`:

```yaml
repo-path:
  - ~/workspace
git:
  username: your-name
  email: your@email.com
github_owner: your-username
```

## Common Commands

### Git Repository Management

```bash
spark git update -p ~/workspace               # Update all repositories
spark git update -p ~/workspace --ssh         # Force SSH when HTTPS is unstable
spark git init --owner variableway            # Initialize a repo and create its GitHub remote
spark git submodule add -p /path/to/repos     # Add existing repos as submodules
spark git batch-clone variableway -o ./repos  # Clone all repos for an org
spark git push-all -p ~/workspace             # Commit and push every repo
spark git scan ~/workspace                    # Scan repos and persist to SQLite
```

### Mirror Switching

```bash
spark magic pip use tsinghua                  # Python → Tsinghua mirror
spark magic go use goproxy                    # Go → goproxy.cn
spark magic node use taobao                   # Node → Taobao mirror
spark magic clean                             # Clean node_modules and .venv
```

### Task Management

```bash
spark task init                               # Initialize the task directory
spark task create my-feature                  # Create an issue file
spark task dispatch my-feature                # Dispatch to the work directory
spark task sync my-feature                    # Sync back to the task directory
```

### Documentation

```bash
spark docs init                               # Create the docs structure
spark docs site                               # Initialize a docmd site
docmd dev                                     # Preview docs locally
```

### Process Diagnostics

```bash
spark witr nginx                              # Inspect the nginx process
spark witr --port 8080                        # Find what is bound to port 8080
spark witr --pid 1234                         # Inspect a process by PID
```

## Next Steps

- [Full Usage Guide](/en/usage/usage)
- [Git Management](/en/usage/git)
- [Project Analysis](/en/analysis/project-analysis)
