# Spark CLI 使用指南

Spark 是一个用于日常开发自动化的 CLI 工具。

## 命令总览

| 命令组 | 说明 |
|--------|------|
| `spark git` | Git 仓库管理（克隆、更新、Gitcode、批量克隆、Issue、推送、扫描） |
| `spark hub` | references 用 registry 扫描和克隆；自研 app 用 collections 登记 |
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
```

## 详细用法

- [Git 仓库管理](./git.md)
- [项目 Hub](./hub.md)
- [系统工具](./magic.md)
- [脚本管理](./script.md)
- [文档管理](./docs-cmd.md)
- [进程诊断](./witr.md)

## 新手上手

| 想要 | 从这里开始 |
|------|------------|
| 一条命令先试试 | `spark magic flush-dns`（零配置）、`spark version` |
| 让 AI 助手用好 spark | [spark-cli Skill](https://github.com/variableway/spark-cli/blob/main/skills/spark-cli/SKILL.md) |
| 学会写 Go CLI | [Golang CLI 入门 · 第一课](../quick-start/golang-cli-101.md) |
| 学会写 Node/TS 工具 | [Node + TypeScript 入门 · 第一课](../quick-start/nodejs-typescript-101.md) |
| 搭一个文档站 | [从零创建文档站](../quick-start/docs-site-from-scratch.md) |
| 命令完整参考 | [命令规格](../spec/git.md) 与 [AGENTS.md 镜像](../Agents.md) |
