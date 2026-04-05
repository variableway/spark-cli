# spark magic — 系统工具

系统级实用工具：DNS 刷新、镜像源切换。

## 命令速查

```bash
spark magic flush-dns                         # 刷新 DNS 缓存

# 镜像源切换（pip / go / node 通用子命令）
spark magic <pip|go|node> list                # 列出可用镜像
spark magic <pip|go|node> use <name>          # 切换镜像源
spark magic <pip|go|node> current             # 查看当前配置
```

---

## spark magic flush-dns

刷新当前系统的 DNS 缓存。

```bash
spark magic flush-dns
```

自动检测操作系统并执行对应命令：
- **macOS**: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
- **Windows**: `ipconfig /flushdns`
- **Linux**: `sudo systemctl restart systemd-resolved`

---

## spark magic pip

管理 Python pip 镜像源。

```bash
spark magic pip list                          # 列出所有可用源
spark magic pip use tsinghua                  # 切换到清华源
spark magic pip use default                   # 恢复官方源
spark magic pip current                       # 查看当前源
```

**可用镜像源:**

| 名称 | URL |
|------|-----|
| `default` | https://pypi.org/simple |
| `tsinghua` | https://pypi.tuna.tsinghua.edu.cn/simple |
| `aliyun` | https://mirrors.aliyun.com/pypi/simple |
| `douban` | https://pypi.doubanio.com/simple |
| `ustc` | https://pypi.mirrors.ustc.edu.cn/simple |
| `tencent` | https://mirrors.cloud.tencent.com/pypi/simple |

配置文件位置: `~/.pip/pip.conf`

---

## spark magic go

管理 Go module 代理设置。

```bash
spark magic go list                           # 列出所有可用代理
spark magic go use goproxy                    # 切换到 goproxy.cn
spark magic go use default                    # 恢复官方代理
spark magic go current                        # 查看当前代理
```

**可用代理:**

| 名称 | URL |
|------|-----|
| `default` | https://proxy.golang.org,direct |
| `aliyun` | https://mirrors.aliyun.com/goproxy/,direct |
| `tsinghua` | https://mirrors.tuna.tsinghua.edu.cn/goproxy/,direct |
| `goproxy` | https://goproxy.cn,direct |
| `ustc` | https://goproxy.ustc.edu.cn,direct |
| `nju` | https://goproxy.njuer.org,direct |

配置方式: `go env -w GOPROXY=<url>`

---

## spark magic node

管理 Node.js npm registry 设置。

```bash
spark magic node list                         # 列出所有可用 registry
spark magic node use taobao                   # 切换到淘宝源
spark magic node use default                  # 恢复官方源
spark magic node current                      # 查看当前 registry
```

**可用 Registry:**

| 名称 | URL |
|------|-----|
| `default` | https://registry.npmjs.org/ |
| `taobao` | https://registry.npmmirror.com/ |
| `aliyun` | https://registry.npmmirror.com/ |
| `tencent` | https://mirrors.cloud.tencent.com/npm/ |
| `huawei` | https://mirrors.huaweicloud.com/repository/npm/ |
| `ustc` | https://npmreg.mirrors.ustc.edu.cn/ |

配置方式: `npm config set registry <url>`
