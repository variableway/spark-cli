# spark magic — Command Spec

System utilities command group: DNS flush and mirror switching.

## Parent

```
spark magic
```

No arguments, no flags.

---

## spark magic flush-dns

Flush the system DNS cache. Supports macOS, Windows, and Linux.

```
spark magic flush-dns
```

No flags, no arguments.

---

## spark magic pip

Manage Python pip mirrors. Subcommands: `list`, `use`, `current`.

### spark magic pip list

List every available pip mirror.

```
spark magic pip list
```

No flags, no arguments.

### spark magic pip use

Switch to the named pip mirror.

```
spark magic pip use <source-name>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `source-name` | string | Yes | Mirror name |

Available mirrors: `default`, `tsinghua`, `aliyun`, `douban`, `ustc`, `tencent`

### spark magic pip current

Print the current pip mirror configuration.

```
spark magic pip current
```

No flags, no arguments.

---

## spark magic go

Manage Go module proxy settings. Subcommands: `list`, `use`, `current`.

### spark magic go list

List every available Go module proxy.

```
spark magic go list
```

No flags, no arguments.

### spark magic go use

Switch to the named Go module proxy.

```
spark magic go use <proxy-name>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `proxy-name` | string | Yes | Proxy name |

Available proxies: `default`, `aliyun`, `tsinghua`, `goproxy`, `ustc`, `nju`

### spark magic go current

Print the current Go proxy configuration.

```
spark magic go current
```

No flags, no arguments.

---

## spark magic node

Manage Node.js npm registry settings. Subcommands: `list`, `use`, `current`.

### spark magic node list

List every available npm registry.

```
spark magic node list
```

No flags, no arguments.

### spark magic node use

Switch to the named npm registry.

```
spark magic node use <registry-name>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `registry-name` | string | Yes | Registry name |

Available registries: `default`, `taobao`, `aliyun`, `tencent`, `huawei`, `ustc`

### spark magic node current

Print the current npm registry configuration.

```
spark magic node current
```

No flags, no arguments.

---

## spark magic clean

Recursively clean `node_modules` and `.venv` directories plus `package-lock.json` files under a project directory.

```
spark magic clean [-m <mode>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-m, --mode` | string | `""` | No | Clean mode: `node`, `python` (default: both) |

No arguments.

**Behavior**:
- Scans the directory passed via `--path` (default: current directory)
- Automatically skips `.git` directories
- `node` mode deletes `node_modules` directories and `package-lock.json` files; `python` mode deletes `.venv` directories
- Lists every item that was cleaned (directories and files)

---

## spark magic copy-config

Deploy the Neovim and Ghostty config templates that are embedded at build time to a target.

```
spark magic copy-config [<user@host:path>]
```

| Flag | Short | Type | Default | Required | Description |
|------|-------|------|---------|----------|-------------|
| — | — | — | — | — | No flags |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `target` | string | No | Target directory, or a remote address in the form `<user@host:path>` (at most 1) |

**Behavior**:
- Template sources live in `internal/templates/dotfiles/` and are embedded into the binary via `//go:embed` at build time
- Without arguments, templates are written to the local default paths `~/.config/nvim/` and `~/.config/ghostty/`
- With a target argument, they deploy to that local directory or to an SSH remote target
- Prefers `rsync` for transfer; local targets fall back to `cp` when `rsync` is missing, while remote targets require `rsync`
