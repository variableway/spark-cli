# Node + TypeScript 入门 · 第一课

面向零基础：用「给文档站写一个 TypeScript 小工具」当例子，搞懂
「一个 Node/TypeScript 项目是怎么炼成的」。

学完你应该能回答四个问题：

1. Node/TS 项目的**基本技术**是什么？
2. 怎么**使用第三方包**（别人写好的轮子）？
3. 怎么**管理依赖**（版本锁定、升级、清理）？
4. **构建与工具链**是怎么分工的？

> 和 [Golang CLI 入门 · 第一课](golang-cli-101.md) 是姊妹篇：那一课讲 Go，
> 这一课讲 Node + TypeScript，用同一个「文档站」当贯穿案例。

---

## 0. 先看一眼成品

本仓库的 `docs/` 就是一个 Node 文档站，它的完整链路只有五步：

```
docs/**.md          Markdown 源文件
   │
   ├─ docmd build    ① 读 Markdown + docmd.config.js → site/
   │
   └─ site/          ② 静态 HTML + 搜索索引 + sitemap
        │
        └─ Actions  ③ push 到 main 自动发布到 GitHub Pages
```

对应的三个文件，你今天会全部用到：

| 文件 | 作用 | Go 里的对应物 |
|------|------|----------------|
| `package.json` | 项目声明 + 依赖清单 + 命令别名 | `go.mod` + `Makefile` |
| `docmd.config.js` | 站点配置（源目录、输出、主题、i18n） | `internal/config` + flag 定义 |
| `tsconfig.json` | TypeScript 编译选项 | `go build` 的编译期约束 |

---

## 1. 基本技术：一个 Node 项目 = 一个 package.json

Node 项目和 Go 项目的差别，第一眼就在**入口**上：

| | Go | Node / TypeScript |
|---|-----|-------------------|
| 入口 | `main.go` → `cmd.Execute()` | `package.json` 的 `main` / `scripts` |
| 命令定义 | Cobra 结构体 | `package.json` 的 `scripts` 字段 |
| 业务代码放哪 | `internal/`（外部不可见） | `src/`（靠约定 + `exports` 限制） |
| 依赖清单 | `go.mod` | `package.json` 的 `dependencies` |
| 依赖锁定 | `go.sum` | `package-lock.json` / `pnpm-lock.yaml` |
| 产物 | 单个二进制 | 一堆 `.js` + `node_modules`（或打包后的单文件） |

### package.json 逐字段拆解

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
    "@docmd/plugin-search": "0.9.8"
  }
}
```

| 字段 | 作用 | 备注 |
|------|------|------|
| `name` / `version` | 项目名与版本 | 私有项目随便填 |
| `private: true` | 禁止意外发布到 npm | 文档站务必加 |
| `type: "module"` | 整个项目用 ESM 语法 | 写成 `commonjs` 则用 `require` |
| `scripts` | 命令别名 | `npm run build` = `docmd build` |
| `dependencies` | 运行时依赖 | 进产物 |
| `devDependencies` | 开发期依赖 | 不进产物（typescript、eslint…） |

> **ESM vs CJS 速记**：现代 Node 默认 ESM，写 `import` / `export`；
> 老项目用 CJS，写 `require` / `module.exports`。两者可以共存：
> `.cjs` 后缀强制 CJS，`.mjs` 后缀强制 ESM。

---

## 2. 使用第三方包

Node 的第三方包也叫「轮子」，从 npm registry 下载。**包名 = 你要用的功能**：

```bash
npm install @docmd/core          # 装一个运行时依赖
npm install -D typescript @types/node   # 装开发期依赖（-D = --save-dev）
npm install docmd@latest         # 装全局命令行工具（不写进 package.json）
```

安装后你会同时得到三样东西，**它们都是结果，不要手改**：

1. `node_modules/` —— 依赖实体落盘
2. `package.json` 的 `dependencies` —— 被自动写入
3. `package-lock.json` —— 锁文件被自动写入

### 在 TypeScript 里怎么用

```ts
// src/index.ts
import { readdir } from "node:fs/promises";
import { join } from "node:path";

export async function listDocs(root: string): Promise<string[]> {
  const entries = await readdir(root, { withFileTypes: true });
  return entries.filter((e) => e.isFile() && e.name.endsWith(".md"))
                .map((e) => join(root, e.name));
}
```

三个要点：

1. **`node:` 前缀**是 Node 内置模块（`node:fs`、`node:path`…）的标准写法
2. **内置模块要装类型**：`npm i -D @types/node`，否则 TS 报「找不到模块」
3. **类型来自包的 `.d.ts`**：第三方包自带类型时不用额外装 `@types/xxx`

### 找不到合适的包怎么办

- npm 生态的关键词：`cli` `parser` `markdown` `static site`
- 官方文档 <https://docs.npmjs.com>
- 实在没有就用 `child_process` 调命令行工具（很多 Node 包只是 CLI 的壳）

---

## 3. 如何管理依赖

| 文件 | 作用 | 类比（Go） |
|------|------|------------|
| `package.json` | 声明：名字、版本范围、脚本 | `go.mod`（但没有校验和） |
| `package-lock.json` | 每个依赖的**精确版本 + 哈希** | `go.sum` |
| `pnpm-lock.yaml` | pnpm 的锁文件 | 同上，格式不同 |
| `node_modules/` | 依赖实体 | `GOMODCACHE` + vendor 目录 |

常用命令：

```bash
npm install            # 按 package.json 装依赖（生成/更新 lockfile）
npm ci                 # 严格按 lockfile 装（CI 首选，永远可复现）
npm outdated           # 看哪些依赖有新版本
npm update <pkg>       # 升级某个依赖
npm uninstall <pkg>    # 移除依赖
npm audit              # 查依赖里的已知漏洞
npm audit fix          # 自动修能修的
```

### 三条好习惯

1. **`package.json` 和 lockfile 一定要提交进 Git**——CI 用 `npm ci` 才能复现你本地的构建
2. **区分 dependencies 和 devDependencies**——`typescript` 这类只服务于构建的工具不该进运行时依赖
3. **CI 里用 `npm ci` 而不是 `npm install`**——前者严格按锁文件装，不会偷偷升级

### 锁文件该用哪个

| 包管理器 | 锁文件 | 特点 |
|----------|--------|------|
| npm | `package-lock.json` | 自带，最省事 |
| pnpm | `pnpm-lock.yaml` | 硬链接共享 store，省磁盘、装得快 |
| yarn | `yarn.lock` | 生态老牌 |

> 三选一，别混用。本仓库用 pnpm（见 `pnpm-lock.yaml`）；
> 团队统一用 npm 就换成 `npm install` + `package-lock.json`。

---

## 4. 构建与工具链

Node 的构建比 Go「松」——**没有编译期**，真正需要编译的只有 TypeScript。

### tsconfig.json：把编译规则写进文件

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"]
}
```

| 选项 | 作用 | 建议 |
|------|------|------|
| `target` | 编译成哪个版本的 JS | `ES2022` |
| `module` / `moduleResolution` | 模块语法与解析方式 | `ESNext` + `bundler` |
| `outDir` / `rootDir` | 输出目录 / 源码目录 | `dist` / `src` |
| `strict` | 打开全部严格检查 | **永远开** |
| `declaration` | 生成 `.d.ts` 类型声明 | 发包时才需要 |
| `sourceMap` | 生成 sourcemap | 调试用 |

### npm scripts = Makefile 的等价物

```json
{
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "typecheck": "tsc --noEmit",
    "build": "tsc",
    "test": "vitest run",
    "lint": "eslint src"
  }
}
```

```bash
npm run dev        # 开发（热重载）
npm run typecheck  # 只做类型检查，不产出文件
npm run build      # 编译到 dist/
npm test           # 跑测试
```

| 你想做的事 | Node | Go |
|------------|------|-----|
| 编译 | `npm run build`（tsc） | `go build` |
| 只查错不产出 | `tsc --noEmit` | `go vet` |
| 跑测试 | `npm test`（vitest/jest） | `go test ./...` |
| 代码风格 | `eslint` + `prettier` | `gofmt` + `golangci-lint` |
| 任务清单 | `package.json` 的 `scripts` | `Makefile` / `Taskfile.yml` |
| 交叉编译 | 一般不需要 | `GOOS=windows go build` |

> Node 项目的「交叉编译」通常不需要——产物是 JS，跨平台天然可用；
> 需要单文件可执行文件时才引入打包器（`esbuild`、`pkg`、`node --experimental-sea`）。

---

## 5. Use case：给文档站写一个 TypeScript 工具

现在把上面的知识串起来：**用 TypeScript 写一个小工具，扫描 `docs/` 下的 Markdown，
自动生成 `navigation.json`**。这是每个文档站都会遇到的需求。

### 5.1 建项目

```bash
mkdir docs-nav-tool && cd docs-nav-tool
npm init -y
npm i -D typescript @types/node tsx
npx tsc --init          # 生成一份 tsconfig.json 再按需修改
```

目录：

```
docs-nav-tool/
├── package.json
├── tsconfig.json
└── src/
    └── nav.ts
```

### 5.2 写代码

```ts
// src/nav.ts
import { readdir, readFile, writeFile } from "node:fs/promises";
import { basename, join, relative } from "node:path";

interface NavItem {
  title: string;
  path: string;
  children?: NavItem[];
}

async function walk(dir: string, root: string): Promise<NavItem[]> {
  const entries = await readdir(dir, { withFileTypes: true });
  const items: NavItem[] = [];

  for (const e of entries) {
    const full = join(dir, e.name);
    if (e.isDirectory()) {
      items.push({
        title: e.name,
        path: "/" + relative(root, full).split(/[\\/]/).join("/"),
        children: await walk(full, root),
      });
      continue;
    }
    if (!e.name.endsWith(".md")) continue;

    // 标题取正文第一个 h1，没有就用文件名
    const body = await readFile(full, "utf8");
    const h1 = body.match(/^#\s+(.+)$/m)?.[1]?.trim();
    items.push({
      title: h1 ?? basename(e.name, ".md"),
      path: "/" + relative(root, full).replace(/\.md$/, "").split(/[\\/]/).join("/"),
    });
  }

  return items.sort((a, b) => a.title.localeCompare(b.title));
}

const [, , srcDir = "docs/zh", outFile = "docs/zh/navigation.json"] = process.argv;
const tree = await walk(srcDir, srcDir);
await writeFile(outFile, JSON.stringify(tree, null, 2), "utf8");
console.log(`wrote ${tree.length} top-level item(s) to ${outFile}`);
```

几个 TypeScript 特有的点，顺手记住：

| 写法 | 含义 |
|------|------|
| `interface NavItem` | 描述对象结构 |
| `async` / `await` | 异步；`Promise<string[]>` 是「将来会得到 string 数组」 |
| `e is File` / `e.isDirectory()` | 目录项类型收窄 |
| `?.` / `??` | 可选链 / 空值合并 |
| `const [, , srcDir = "docs/zh"]` | 数组解构 + 默认值 |

### 5.3 接进 scripts

```json
{
  "type": "module",
  "scripts": {
    "nav": "tsx src/nav.ts docs/zh docs/zh/navigation.json",
    "typecheck": "tsc --noEmit",
    "build": "tsc"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "tsx": "^4.0.0",
    "typescript": "^5.5.0"
  }
}
```

```bash
npm run nav         # 生成 navigation.json
npm run typecheck   # 类型检查（提交前跑一遍）
```

### 5.4 接进 CI

在 GitHub Actions 里，类型检查和构建都能挂上：

```yaml
name: CI
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run typecheck
      - run: npm run build
```

> `npm ci` + lockfile + `cache: npm`，是 Node 项目 CI 的标准三件套。

---

## 6. 和 Go 一次说清

| 维度 | Go | Node + TypeScript |
|------|-----|--------------------|
| 依赖清单 | `go.mod` | `package.json` |
| 锁文件 | `go.sum` | `package-lock.json` / `pnpm-lock.yaml` |
| 装依赖 | `go mod download` | `npm ci` |
| 清理依赖 | `go mod tidy` | `npm prune` / 删掉重装 |
| 编译 | `go build` | `tsc` |
| 类型检查 | 编译时自带 | `tsc --noEmit` |
| 任务清单 | `Makefile` / `Taskfile.yml` | `package.json` 的 `scripts` |
| 产物 | 单二进制，跨平台需交叉编译 | `.js` 文件，跨平台通用 |
| 分发 | `go install` / 编译后拷走 | 发布到 npm，或 `npm i -g` |

---

## 附录 A：课程 Prompt（复制给 AI 助手即可开课）

```text
你是我的 Node + TypeScript 入门导师。我是零基础，请用「给文档站写一个
navigation.json 生成工具」作为贯穿案例，按下面四课教我，每课：
概念一句话 + 一个能跑的小例子 + 一个小练习。
1) 基本技术：package.json / scripts / src/ 的分工，ESM 与 CJS 的区别
2) 使用第三方包：npm install、node: 内置模块、@types 类型包
3) 依赖管理：lockfile、npm ci 与 npm install 的区别、npm audit
4) 构建与工具链：tsconfig.json、tsc、eslint/prettier、CI 里的 npm ci
要求：一次只讲一课；优先用真实项目文件举例；练习题要能在 5 分钟内做完；
我答完再进下一课。
```

## 附录 B：Skill（SKILL.md，可安装为 Agent 技能）

保存为 `SKILL.md`（如放到 `~/.codex/skills/nodejs-typescript-101/SKILL.md`
或 `.claude/skills/nodejs-typescript-101/SKILL.md`）即可作为
「Node/TS 第一课」技能调用：

```markdown
---
name: nodejs-typescript-101
description: Node.js + TypeScript 零基础入门第一课。当用户想学习用
  TypeScript 写工具、看懂 package.json/tsconfig.json，或要求
  "Node 入门/TS 入门/第一课"时使用。
---

# Node + TypeScript 入门第一课

用「文档站 navigation.json 生成器」做贯穿案例，按顺序教四课，
每课一个 5 分钟练习：

1. **基本技术** — `package.json` 的 name/scripts/type、ESM 与 CJS；
   演示 `npm init -y` → `npm run dev`。
2. **第三方包** — `npm install` / `-D`；`node:` 内置模块；`@types/node`
   为何必须装；演示读取 `docs/` 目录。
3. **依赖管理** — `package-lock.json` vs `pnpm-lock.yaml`；`npm ci`
   与 `npm install` 的差异；`npm audit`。
4. **构建与工具链** — `tsconfig.json` 关键项、`tsc --noEmit`、npm scripts
   当作 Makefile 用、CI 中 `npm ci` + typecheck。

教学规则：一次一课；中文讲解、代码保持英文；每课结束出 1 道练习并等待
作答；全部完成后给出「继续深入」的三个方向（单元测试、类型体操、打包成单文件）。
```

---

下一步：在你的文档站项目里跑一遍 `npm run nav && npm run typecheck`，
再把 `docs/` 交给 docmd 构建——你就完成了第一课的毕业项目。
