# 系统工具

## 功能概述

`spark magic` 提供日常开发中的系统工具，包括 DNS 缓存刷新和包管理器镜像源切换。

## 核心能力

### DNS 刷新

一键刷新系统 DNS 缓存，支持 macOS、Windows、Linux。

```bash
spark magic flush-dns
```

### Python pip 镜像源切换

管理 pip 的镜像源配置，解决国内访问 PyPI 速度慢的问题。

```bash
spark magic pip list          # 列出可用源
spark magic pip use tsinghua  # 切换到清华源
spark magic pip current       # 查看当前源
```

可用镜像源：

| 名称 | 说明 |
|------|------|
| `tsinghua` | 清华大学 |
| `aliyun` | 阿里云 |
| `douban` | 豆瓣 |
| `ustc` | 中国科技大学 |
| `tencent` | 腾讯云 |

### Go Module Proxy 切换

管理 Go module proxy 配置。

```bash
spark magic go list         # 列出可用 proxy
spark magic go use goproxy  # 切换到 goproxy.cn
spark magic go current      # 查看当前 proxy
```

可用 Proxy：

| 名称 | 说明 |
|------|------|
| `aliyun` | 阿里云 |
| `tsinghua` | 清华大学 |
| `goproxy` | goproxy.cn |
| `ustc` | 中国科技大学 |
| `nju` | 南京大学 |

### Node.js npm Registry 切换

管理 npm registry 配置。

```bash
spark magic node list       # 列出可用 registry
spark magic node use taobao # 切换到淘宝源
spark magic node current    # 查看当前 registry
```

可用 Registry：

| 名称 | 说明 |
|------|------|
| `taobao` | 淘宝 |
| `aliyun` | 阿里云 |
| `tencent` | 腾讯云 |
| `huawei` | 华为云 |
| `ustc` | 中国科技大学 |

## 使用参数

三个镜像切换命令（pip/go/node）共享相同的子命令结构：

| 子命令 | 参数 | 说明 |
|--------|------|------|
| `list` | 无 | 列出可用源 |
| `use` | `<name>` | 切换到指定源 |
| `current` | 无 | 显示当前配置 |

## 相关文档

- [Magic 命令规格](../spec/magic.md)
