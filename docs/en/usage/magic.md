# spark magic — System Utilities

System-level utilities: DNS flush, directory cleaning, dotfile deploy, mirror switching.

## Quick Reference

```bash
spark magic flush-dns                         # Flush the DNS cache
spark magic clean [-m node|python]            # Clean node_modules and .venv
spark magic copy-config [<user@host:path>]    # Deploy built-in nvim + ghostty templates

# Mirror switching (pip / go / node share the same subcommands)
spark magic <pip|go|node> list                # List available mirrors
spark magic <pip|go|node> use <name>          # Switch mirror
spark magic <pip|go|node> current             # Show the current configuration
```

---

## spark magic flush-dns

Flush the system DNS cache.

```bash
spark magic flush-dns
```

Auto-detects the OS and runs the appropriate command:
- **macOS**: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
- **Windows**: `ipconfig /flushdns`
- **Linux**: `sudo systemctl restart systemd-resolved`

---

## spark magic clean

Recursively clean `node_modules` and `.venv` directories under a project directory.

```bash
spark magic clean                             # Clean both
spark magic clean -m node                     # Only node_modules
spark magic clean -m python                   # Only .venv
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-m, --mode` | | | Clean mode: `node`, `python` (default: both) |

**Behavior**:
- Scans the directory passed via `--path` (default: current directory)
- Automatically skips `.git` directories
- Lists every directory that was cleaned

---

## spark magic copy-config

Deploy the Neovim and Ghostty config templates that are embedded at build time to a destination. Template sources live in `internal/templates/dotfiles/` and are packaged into the binary via `//go:embed`.

```bash
spark magic copy-config                       # Deploy to the local ~/.config/{nvim,ghostty}
spark magic copy-config user@192.168.1.100:~/ # Deploy over SSH to a remote host
spark magic copy-config /mnt/usb/backup/      # Deploy to a custom local path
```

**Behavior**:
- With no argument, writes to the local default paths (`~/.config/nvim/`, `~/.config/ghostty/`)
- Prefers `rsync`; falls back to `cp` for local targets
- Templates are a starting point — edit `internal/templates/dotfiles/` and rebuild to customize

---

## spark magic pip

Manage Python pip mirrors.

```bash
spark magic pip list                          # List every available mirror
spark magic pip use tsinghua                  # Switch to the Tsinghua mirror
spark magic pip use default                   # Restore the official index
spark magic pip current                       # Show the current mirror
```

**Available mirrors:**

| Name | URL |
|------|-----|
| `default` | https://pypi.org/simple |
| `tsinghua` | https://pypi.tuna.tsinghua.edu.cn/simple |
| `aliyun` | https://mirrors.aliyun.com/pypi/simple |
| `douban` | https://pypi.doubanio.com/simple |
| `ustc` | https://pypi.mirrors.ustc.edu.cn/simple |
| `tencent` | https://mirrors.cloud.tencent.com/pypi/simple |

Config file location: `~/.pip/pip.conf`

---

## spark magic go

Manage Go module proxy settings.

```bash
spark magic go list                           # List every available proxy
spark magic go use goproxy                    # Switch to goproxy.cn
spark magic go use default                    # Restore the official proxy
spark magic go current                        # Show the current proxy
```

**Available proxies:**

| Name | URL |
|------|-----|
| `default` | https://proxy.golang.org,direct |
| `aliyun` | https://mirrors.aliyun.com/goproxy/,direct |
| `tsinghua` | https://mirrors.tuna.tsinghua.edu.cn/goproxy/,direct |
| `goproxy` | https://goproxy.cn,direct |
| `ustc` | https://goproxy.ustc.edu.cn,direct |
| `nju` | https://goproxy.njuer.org,direct |

Configured via: `go env -w GOPROXY=<url>`

---

## spark magic node

Manage the Node.js npm registry.

```bash
spark magic node list                         # List every available registry
spark magic node use taobao                   # Switch to the Taobao registry
spark magic node use default                  # Restore the official registry
spark magic node current                      # Show the current registry
```

**Available registries:**

| Name | URL |
|------|-----|
| `default` | https://registry.npmjs.org/ |
| `taobao` | https://registry.npmmirror.com/ |
| `aliyun` | https://registry.npmmirror.com/ |
| `tencent` | https://mirrors.cloud.tencent.com/npm/ |
| `huawei` | https://mirrors.huaweicloud.com/repository/npm/ |
| `ustc` | https://npmreg.mirrors.ustc.edu.cn/ |

Configured via: `npm config set registry <url>`
