# spark docs — 命令规格

文档管理命令组。

## 父命令

```
spark docs
```

无参数，无标志。

---

## spark docs init

创建标准文档目录结构。

生成的目录结构：
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

```
spark docs init [--root <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--root` | string | `.` | 否 | 项目根目录 |

无参数。

---

## spark docs site

初始化 docmd 文档站点配置。功能：
- 自动从 git remote 检测项目名称和 GitHub Pages URL
- 生成 `docmd.config.js`（sky 主题、SPA 布局、搜索/mermaid/llms 插件）
- 如果 docmd 未安装，自动全局安装 `@docmd/core`
- 如果 `package.json` 不存在，自动初始化

```
spark docs site [--root <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--root` | string | `.` | 否 | 项目根目录 |

无参数。

初始化完成后运行：
```bash
docmd dev      # 本地预览
docmd build    # 构建静态站点
```
