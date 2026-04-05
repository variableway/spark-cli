# Spark CLI 使用指南

Spark 是一个用于日常开发自动化和 AI Skill 集成的 CLI 工具。

## 命令总览

| 命令组 | 说明 |
|--------|------|
| `spark git` | Git 仓库管理（更新、Mono-repo、子模块同步、Gitcode） |
| `spark agent` | AI Agent 配置管理（Claude Code、Codex、Kimi、GLM） |
| `spark task` | 任务管理（创建、分发、同步、实现） |
| `spark script` | 自定义脚本管理 |
| `spark magic` | 系统工具（DNS 刷新、镜像源切换） |
| `spark docs` | 文档管理（初始化结构、站点配置） |

## 全局标志

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | | `~/.spark.yaml` | 配置文件路径 |
| `--path` | `-p` | `.` | 扫描目录（可多次指定） |

## 配置文件

配置文件位于 `~/.spark.yaml`：

```yaml
repo-path:
  - ~/workspace
  - ~/projects
git:
  username: your-name
  email: your@email.com
task_dir: ./tasks
github_owner: your-username
work_dir: ./workspace
```

## 详细用法

- [Git 仓库管理](./git.md)
- [AI Agent 配置](./agent.md)
- [任务管理](./task.md)
- [系统工具](./magic.md)
- [脚本管理](./script.md)
- [文档管理](./docs-cmd.md)
