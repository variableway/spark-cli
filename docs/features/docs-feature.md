# 文档管理

## 功能概述

`spark docs` 管理项目文档结构和 docmd 站点配置。一键创建标准文档目录，自动生成 docmd 配置文件。

## 核心能力

### 文档目录初始化

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

已存在的文件和目录会被跳过，不会覆盖。

```bash
spark docs init
spark docs init --root /path/to/project
```

### docmd 站点初始化

自动生成 docmd 配置文件 `docmd.config.js`：
- 从 git remote 自动检测项目名称和 GitHub Pages URL
- 配置 sky 主题、SPA 布局
- 启用搜索、Mermaid 图表、LLM 全文索引等插件
- 自动安装 `@docmd/core`（如果未安装）
- 自动初始化 `package.json`（如果不存在）

```bash
spark docs site
spark docs site --root /path/to/project
```

初始化后可运行：
```bash
docmd dev      # 本地预览
docmd build    # 构建静态站点
```

## 使用参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--root` | string | `.` | 项目根目录 |

## 依赖

- Node.js（docmd 站点功能）
- `@docmd/core`（自动安装）

## 相关文档

- [Docs 命令规格](../spec/docs-cmd.md)
- [Docs 使用指南](../usage/docs-cmd.md)
