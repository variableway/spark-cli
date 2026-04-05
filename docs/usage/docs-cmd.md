# spark docs — 文档管理

管理项目文档结构和 docmd 站点配置。

## 命令速查

```bash
spark docs init [--root <path>]               # 创建文档目录结构
spark docs site [--root <path>]               # 初始化 docmd 站点配置
```

---

## spark docs init

创建标准文档目录结构：

```
docs/
├── Agents.md
├── analysis/
├── features/
├── index.md
├── quick-start/
├── README.md
├── spec/
├── tips/
└── usage/
```

已存在的文件和目录会被跳过。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--root` | `.` | 项目根目录 |

```bash
spark docs init                               # 在当前目录创建
spark docs init --root /path/to/project       # 在指定项目创建
```

---

## spark docs site

初始化 docmd 文档站点配置：

- 自动从 git remote 检测项目名称和 GitHub Pages URL
- 生成 `docmd.config.js`（sky 主题、SPA 布局、搜索/mermaid/llms 插件）
- 如果 docmd 未安装，自动全局安装 `@docmd/core`
- 如果 `package.json` 不存在，自动初始化

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--root` | `.` | 项目根目录 |

```bash
spark docs site                               # 在当前目录初始化
spark docs site --root /path/to/project       # 在指定项目初始化
```

初始化完成后运行：

```bash
docmd dev                                     # 本地预览
docmd build                                   # 构建静态站点
```

## 相关命令

- [脚本管理](./script.md)
- [任务管理](./task.md)
