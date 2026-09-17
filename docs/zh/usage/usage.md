# Spark CLI 使用指南

Spark 是一个用于日常开发自动化和 AI Skill 集成的 CLI 工具。

## 命令总览

| 命令组 | 说明 |
|--------|------|
| `spark git` | Git 仓库管理（克隆、更新、子模块、Gitcode、批量克隆、Issue、推送、扫描） |
| `spark repo` | 仓库管理（registry 文件驱动的 scan / clone / list） |
| `spark script` | 自定义脚本管理 |
| `spark magic` | 系统工具（DNS 刷新、目录清理、dotfiles 部署、镜像源切换） |
| `spark docs` | 文档管理（初始化结构、站点配置） |
| `spark witr` | 进程诊断（Why Is This Running） |
| `spark version` | 显示 version / commit / build date |

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
  scanner:
    db: ~/.innate/feeds.db
gitlab:
  host: gitlab.example.com   # 可选：把 token 限定到该实例
  token: glpat-xxxx
github-owner: your-username  # spark git init --owner 默认值
```

## 详细用法

- [Git 仓库管理](./git.md)
- [仓库管理](./repo.md)
- [系统工具](./magic.md)
- [脚本管理](./script.md)
- [文档管理](./docs-cmd.md)
- [进程诊断](./witr.md)
