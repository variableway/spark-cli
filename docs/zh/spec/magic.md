# spark magic — 命令规格

系统工具命令组，提供 DNS 刷新和镜像源切换功能。

## 父命令

```
spark magic
```

无参数，无标志。

---

## spark magic flush-dns

刷新系统 DNS 缓存。支持 macOS、Windows、Linux。

```
spark magic flush-dns
```

无标志，无参数。

---

## spark magic pip

管理 Python pip 镜像源。子命令：`list`、`use`、`current`。

### spark magic pip list

列出所有可用的 pip 镜像源。

```
spark magic pip list
```

无标志，无参数。

### spark magic pip use

切换到指定的 pip 镜像源。

```
spark magic pip use <source-name>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source-name` | string | 是 | 镜像源名称 |

可用镜像源：`default`、`tsinghua`、`aliyun`、`douban`、`ustc`、`tencent`

### spark magic pip current

显示当前 pip 镜像源配置。

```
spark magic pip current
```

无标志，无参数。

---

## spark magic go

管理 Go module proxy 设置。子命令：`list`、`use`、`current`。

### spark magic go list

列出所有可用的 Go module proxy。

```
spark magic go list
```

无标志，无参数。

### spark magic go use

切换到指定的 Go module proxy。

```
spark magic go use <proxy-name>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `proxy-name` | string | 是 | Proxy 名称 |

可用 proxy：`default`、`aliyun`、`tsinghua`、`goproxy`、`ustc`、`nju`

### spark magic go current

显示当前 Go proxy 配置。

```
spark magic go current
```

无标志，无参数。

---

## spark magic node

管理 Node.js npm registry 设置。子命令：`list`、`use`、`current`。

### spark magic node list

列出所有可用的 npm registry。

```
spark magic node list
```

无标志，无参数。

### spark magic node use

切换到指定的 npm registry。

```
spark magic node use <registry-name>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `registry-name` | string | 是 | Registry 名称 |

可用 registry：`default`、`taobao`、`aliyun`、`tencent`、`huawei`、`ustc`

### spark magic node current

显示当前 npm registry 配置。

```
spark magic node current
```

无标志，无参数。

---

## spark magic clean

递归清理项目目录中的 `node_modules`、`.venv` 目录和 `package-lock.json` 文件。

```
spark magic clean [-m <mode>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-m, --mode` | string | `""` | 否 | 清理模式：`node`、`python`（默认两者） |

无参数。

**行为**：
- 扫描 `--path` 指定的目录（默认当前目录）
- 自动跳过 `.git` 目录
- `node` 模式删除 `node_modules` 目录和 `package-lock.json` 文件；`python` 模式删除 `.venv` 目录
- 列出所有被清理的项（目录与文件）

---

## spark magic copy-config

部署编译时嵌入的 Neovim 与 Ghostty 配置模板到目标位置。

```
spark magic copy-config [<user@host:path>]
```

| 标志 | 简写 | 类型 | 默认值 | 必填 | 说明 |
|------|------|------|--------|------|------|
| — | — | — | — | — | 无标志 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target` | string | 否 | 目标目录，或 `<user@host:path>` 形式的远程地址（最多 1 个） |

**行为**：
- 模板源码位于 `internal/templates/dotfiles/`，构建时通过 `//go:embed` 嵌入二进制
- 无参数时写入本机默认路径 `~/.config/nvim/`、`~/.config/ghostty/`
- 带参数时部署到该本地目录或 SSH 远程目标
- 优先使用 `rsync` 传输；本地目标在缺少 `rsync` 时回退到 `cp`，远程目标必须使用 `rsync`
