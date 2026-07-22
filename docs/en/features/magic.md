# System Utilities

## Overview

`spark magic` provides day-to-day system utilities: DNS cache flushing and package-manager mirror switching.

## Core Capabilities

### DNS Flush

One-shot DNS cache flush; supports macOS, Windows, and Linux.

```bash
spark magic flush-dns
```

### Python pip Mirror Switching

Manage pip mirror configuration to alleviate slow PyPI access in China.

```bash
spark magic pip list          # List available mirrors
spark magic pip use tsinghua  # Switch to the Tsinghua mirror
spark magic pip current       # Show the current mirror
```

Available mirrors:

| Name | Provider |
|------|----------|
| `tsinghua` | Tsinghua University |
| `aliyun` | Alibaba Cloud |
| `douban` | Douban |
| `ustc` | University of Science and Technology of China |
| `tencent` | Tencent Cloud |

### Go Module Proxy Switching

Manage Go module proxy configuration.

```bash
spark magic go list         # List available proxies
spark magic go use goproxy  # Switch to goproxy.cn
spark magic go current      # Show the current proxy
```

Available proxies:

| Name | Provider |
|------|----------|
| `aliyun` | Alibaba Cloud |
| `tsinghua` | Tsinghua University |
| `goproxy` | goproxy.cn |
| `ustc` | University of Science and Technology of China |
| `nju` | Nanjing University |

### Node.js npm Registry Switching

Manage the npm registry configuration.

```bash
spark magic node list       # List available registries
spark magic node use taobao # Switch to the Taobao mirror
spark magic node current    # Show the current registry
```

Available registries:

| Name | Provider |
|------|----------|
| `taobao` | Taobao |
| `aliyun` | Alibaba Cloud |
| `tencent` | Tencent Cloud |
| `huawei` | Huawei Cloud |
| `ustc` | University of Science and Technology of China |

### Project Directory Cleaning

Recursively clean `node_modules` and `.venv` directories to free disk space.

```bash
spark magic clean           # Clean both
spark magic clean -m node   # Only node_modules
spark magic clean -m python # Only .venv
```

## Parameters

The three mirror-switch commands (pip/go/node) share the same subcommand structure:

| Subcommand | Argument | Description |
|------------|----------|-------------|
| `list` | — | List available mirrors |
| `use` | `<name>` | Switch to the named mirror |
| `current` | — | Show the current configuration |

## Related

- [Magic Command Spec](/en/spec/magic)
