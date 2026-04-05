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

可用镜像源：`tsinghua`、`aliyun`、`douban`、`ustc`、`tencent`

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

可用 proxy：`aliyun`、`tsinghua`、`goproxy`、`ustc`、`nju`

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

可用 registry：`taobao`、`aliyun`、`tencent`、`huawei`、`ustc`

### spark magic node current

显示当前 npm registry 配置。

```
spark magic node current
```

无标志，无参数。
