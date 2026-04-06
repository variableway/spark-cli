# 快速开始

## 安装

```bash
git clone https://github.com/variableway/spark-cli.git
cd spark-cli
make build
```

`make build` 编译二进制文件并安装到 `~/.local/bin/spark`。确保该路径在 `$PATH` 中。

## 配置

创建 `~/.spark.yaml`：

```yaml
repo-path:
  - ~/workspace
git:
  username: your-name
  email: your@email.com
github_owner: your-username
```

## 常用命令

### Git 仓库管理

```bash
spark git update -p ~/workspace               # 更新所有仓库
spark git create -n my-mono -o ./output       # 创建 Mono-repo
spark git batch-clone variableway -o ./repos  # 克隆组织仓库
```

### 镜像源切换

```bash
spark magic pip use tsinghua                  # Python → 清华源
spark magic go use goproxy                    # Go → goproxy.cn
spark magic node use taobao                   # Node → 淘宝源
```

### AI Agent 配置

```bash
spark agent list                              # 查看支持的 Agent
spark agent view claude-code                  # 查看 Claude Code 配置
spark agent profile add my-profile -t glm     # 创建 Profile
spark agent use my-profile                    # 应用到当前项目
```

### 任务管理

```bash
spark task init                               # 初始化任务目录
spark task create my-feature                  # 创建特性文件
spark task dispatch my-feature                # 分发到工作目录
spark task sync my-feature                    # 同步回任务目录
```

### 文档管理

```bash
spark docs init                               # 创建文档结构
spark docs site                               # 初始化 docmd 站点
docmd dev                                     # 本地预览文档
```

## 下一步

- [完整使用指南](../usage/usage.md)
- [Git 管理](../usage/git.md)
- [AI Agent 配置](../usage/agent.md)
- [项目分析报告](../analysis/project-analysis.md)
