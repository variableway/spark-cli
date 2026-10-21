# 从零创建文档站并发布到 GitHub Pages

面向零基础的另一半教程：[从零创建 Go CLI 项目](golang-project-from-scratch.md)
讲二进制，本篇讲 **Node 体系**——用 `npm init` 起步、用 docmd 生成文档站、
用 GitHub Actions 自动发布到 GitHub Pages。本站（spark-cli 文档站）就是
照这个流程搭起来的。

学完你将拥有：

1. 一个带 `package.json` 的标准 Node 项目
2. docmd 驱动的 Markdown 文档站（本地可预览）
3. 推送到 main 即自动发布的 GitHub Pages 站点
4. 一个可以安装给 AI 助手的 SKILL 文档

---

## 0. 准备工作

安装 Node.js 20+（<https://nodejs.org/>），包管理器用 npm（自带）或
[pnpm](https://pnpm.io/) 均可，本篇两种写法都给出。验证：

```bash
node -v     # v20.x 或更高
npm -v
```

## 1. 第一步：`npm init` —— package.json 是怎么来的

Node 项目的起点同样是**声明一个项目**：

```bash
mkdir my-docs && cd my-docs
npm init -y
```

`-y` 表示所有问题都用默认值。生成的 `package.json`：

```json
{
  "name": "my-docs",
  "version": "0.0.1",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "docmd dev",
    "build": "docmd build",
    "preview": "npx serve site"
  },
  "dependencies": {
    "@docmd/core": "^0.9.8",
    "@docmd/plugin-search": "0.9.8",
    "@docmd/plugin-seo": "0.9.8",
    "@docmd/plugin-sitemap": "0.9.8"
  }
}
```

（上面是**装完依赖后**的最终形态；`npm init -y` 初始只有前几个字段。）
逐个字段解释：

| 字段 | 作用 | 备注 |
|------|------|------|
| `name` / `version` | 项目名与版本 | 发布到 npm 才有意义，私有项目随便填 |
| `private: true` | 禁止意外发布到 npm | 文档站项目务必加上 |
| `type: "module"` | 整个项目用 ES Module 语法 | docmd 的配置文件用 `export default`，必须加 |
| `scripts` | 命令别名 | `npm run build` = `docmd build`，把长命令变短 |
| `dependencies` | 生产依赖清单 | 由 `npm install <pkg>` 自动写入 |

和 Go 完全对得上的对照表：

| Go | Node（本项目） | 作用 |
|----|----------------|------|
| `go.mod` | `package.json` | 声明项目与依赖 |
| `go.sum` | `package-lock.json` / `pnpm-lock.yaml` | 锁定依赖版本 |
| `go get <pkg>` | `npm install <pkg>` | 添加依赖 |
| `go mod tidy` | `npm install` | 按声明安装依赖 |
| `go build` | `npm run build` | 生成产物 |
| GOMODCACHE | `node_modules`（pnpm 则是硬链接自 store） | 依赖落盘位置 |

## 2. 第二步：安装 docmd

[docmd](https://docmd.dev) 是本站使用的文档站生成器：读 Markdown，产静态 HTML，
自带搜索 / 主题切换 / 中英双语 / mermaid / sitemap。

```bash
npm install @docmd/core @docmd/plugin-search @docmd/plugin-seo @docmd/plugin-sitemap
```

装完会发生三件事：`node_modules/` 出现依赖、`package.json` 的
`dependencies` 被更新、lockfile 被写入——**这三个都是结果，不要手改**。

spark 用到的另外两个插件（按需选装）：

| 插件 | 作用 |
|------|------|
| `@docmd/plugin-llms` | 生成 `llms.txt`，方便 AI 助手读取全站内容 |
| `@docmd/plugin-mermaid` | 渲染 Mermaid 图表 |

> pnpm 用户把 `npm install` 换成 `pnpm add` / `pnpm install` 即可，
> 依赖以硬链接方式来自全局 store（Windows 上可把 store 指到 D 盘省 C 盘，
> 见 [How to Build](../usage/how-to-build.md)）。

## 3. 第三步：`docmd.config.js` —— 站点的总开关

项目根目录新建 `docmd.config.js`（精简自本仓库真实配置）：

```js
// docmd.config.js
export default defineConfig({
  title: 'My Docs',
  url: 'https://<you>.github.io/my-docs',   // 部署地址，影响 sitemap 与 SEO

  src: 'docs',       // Markdown 源文件目录
  out: 'site',       // 构建产物目录（gitignore 掉）

  layout: {
    sidebar: { collapsible: true },         // 侧边栏可折叠
  },
  theme: { name: 'sky' },                   // 内置主题

  i18n: {
    default: 'zh',                          // 默认语言渲染在根 URL
    locales: [
      { id: 'zh', label: '简体中文' },
      { id: 'en', label: 'English' },       // 英文渲染在 /en/
    ],
  },

  plugins: {
    search: {},                             // 对应已安装的 @docmd/plugin-search
    sitemap: { defaultChangefreq: 'weekly' },
  },
});
```

关键段解释：

- **`src` / `out`**：输入输出。`site/` 是纯静态文件，随时可删掉重建
- **`title` / `url`**：站点元信息，`url` 要与 GitHub Pages 最终地址一致
- **`i18n`**：`default` 语言渲染在根 URL，其他语言自动挂在 `/<locale>/` 下；
  每种语言一个目录（`docs/zh/`、`docs/en/`），各自的
  `navigation.json` 定义侧边栏
- **`plugins`**：键名对应 `@docmd/plugin-*` 包，`{}` 即启用默认配置

## 4. 第四步：写第一篇文档

```
docs/
├── zh/
│   ├── index.md             # 站点首页（h1 会成为页面标题）
│   ├── navigation.json      # 中文侧边栏
│   └── quick-start/
│       └── hello.md         # 你的第一篇文档
└── en/                      # 英文镜像（结构必须与 zh/ 平行）
```

`docs/zh/navigation.json`：

```json
[
  { "title": "首页", "path": "/" },
  {
    "title": "快速开始",
    "icon": "rocket",
    "collapsible": true,
    "children": [
      { "title": "Hello", "path": "/quick-start/hello" }
    ]
  }
]
```

正文就是普通 Markdown；页面标题自动取第一个 `#`，无需 front matter。
双语站点的规则：**每新增一页，`zh/` 与 `en/` 各写一份，两个
`navigation.json` 同步登记**（翻译没跟上时 docmd 会自动回退到默认语言，
不会 404）。

## 5. 第五步：本地开发与构建

```bash
npm run dev       # docmd dev：本地开发服务器，改 Markdown 即时刷新
npm run build     # docmd build：产出到 site/
npm run preview   # npx serve site：像线上一样预览静态产物
```

`site/` 里是自包含的静态 HTML + 搜索索引 + sitemap，**加入 `.gitignore`**
（构建产物不入库，CI 里现构建）。

## 6. 第六步：发布到 GitHub Pages

推荐「GitHub Actions + Pages artifact」方式——推送到 main 自动构建发布，
本仓库的 `.github/workflows/docs.yml` 全文如下（可直接复制）：

```yaml
name: Deploy Docs to GitHub Pages

on:
  push:
    branches: [main]
    paths:              # 只有文档变了才触发，省 runner 时间
      - 'docs/**'
      - 'docmd.config.js'
  workflow_dispatch:    # 保留手动触发入口

permissions:
  contents: read
  pages: write          # 允许写入 Pages
  id-token: write       # OIDC 部署凭证

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - name: Install dependencies
        run: npm install
      - name: Build docs
        run: npx docmd build
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with: { path: site }      # 把 site/ 打包成 Pages artifact

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4   # 把 artifact 发布上线
```

三步开通：

1. 把上面的 workflow 存为 `.github/workflows/docs.yml` 并提交
2. 仓库 **Settings → Pages → Build and deployment → Source** 选
   **GitHub Actions**（不要选分支，选了分支模式 Actions 方式不生效）
3. 推送到 main。Actions 跑完后访问 `https://<you>.github.io/my-docs/`

之后每次改动 `docs/**` 或 `docmd.config.js` 并合入 main，站点自动更新——
这就是本站的发布方式。

> 手动发布也行（不推荐）：本地 `npm run build` 后把 `site/` 推到
> `gh-pages` 分支，Pages Source 选该分支。缺点是容易忘、容易漏 lockfile。

## 7. 用 spark 加速以上全部

spark 把本教程的脚手架做成了命令：

```bash
spark docs init    # 创建 docs/ 标准目录结构（usage/ spec/ features/ ...，已存在则跳过）
spark docs site    # 从 git remote 自动探测标题与 Pages 地址，生成 docmd.config.js，
                   # 缺 package.json 时自动 npm init -y，并装好 docmd 依赖
```

详见 [文档管理命令](../usage/docs-cmd.md)。

---

## 附录：SKILL —— docs-site-from-scratch

保存为 `SKILL.md`（如 `.claude/skills/docs-site-from-scratch/SKILL.md`），
AI 助手即可帮你从零搭建 docmd 文档站并发布到 GitHub Pages：

```markdown
---
name: docs-site-from-scratch
description: 从零创建 docmd 文档站并发布到 GitHub Pages（npm init、package.json、
  docmd.config.js、navigation.json、双语 i18n、Actions 自动部署）。当用户要求
  "搭文档站 / 建文档项目 / 发布文档到 GitHub Pages"时使用。
---

# 从零创建 docmd 文档站

按以下顺序执行，每步完成后向用户确认再继续：

1. **项目初始化** — npm init -y；package.json 必须含 "private": true 与
   "type": "module"（docmd 配置用 ESM）；解释 scripts 与 dependencies 的作用。
2. **安装 docmd** — npm install @docmd/core + 按需插件（search/seo/sitemap/llms/mermaid）；
   提醒 node_modules 与 lockfile 是安装结果，不要手改。
3. **写 docmd.config.js** — src/out/title/url 四要素；多语言用 i18n.locales
   （default 渲染在根 URL，其他在 /<locale>/）；plugins 键名对应插件包。
4. **组织文档** — docs/<locale>/ 目录 + 每语言一份 navigation.json；正文纯
   Markdown，标题取 h1；双语站点每新增一页两个 locale 同步登记。
5. **本地验证** — npm run dev 预览 → npm run build 产出到 site/ →
   site/ 加入 .gitignore。
6. **发布** — 写 .github/workflows/docs.yml（push main + paths 过滤 +
   upload-pages-artifact + deploy-pages 两段式）；仓库 Settings → Pages →
   Source 选 GitHub Actions；推送验证。
   若目标仓库装有 spark-cli，可用 spark docs init / spark docs site 代替 3-4 步。

参考实现：github.com/variableway/spark-cli 的 docs/（zh 默认 + en 镜像），
docmd.config.js 与 .github/workflows/docs.yml 可直接对照。
```

---

## 延伸阅读

- [从零创建 Go CLI 项目](golang-project-from-scratch.md) —— 本项目的另一半：Go 体系
- [How to Build — 构建指南](../usage/how-to-build.md) —— Go 与 Node 构建对照、pnpm 全局地址
- [文档管理命令](../usage/docs-cmd.md) —— `spark docs init` / `spark docs site`
