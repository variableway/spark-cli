# Node + TypeScript Essentials · Lesson 1

For absolute beginners: use "write a small TypeScript tool for a docs site"
as the running example and understand how a Node/TypeScript project is built.

By the end you should be able to answer four questions:

1. What is the **basic tech** of a Node/TS project?
2. How do you **use third-party packages** (wheels other people wrote)?
3. How do you **manage dependencies** (version locking, upgrading, cleanup)?
4. How do the **build and toolchain** divide the work?

> Sister article to [Golang CLI Essentials · Lesson 1](golang-cli-101.md):
> that one teaches Go, this one teaches Node + TypeScript, with the same
> "docs site" as the running case.

---

## 0. Look at the finished product first

The `docs/` directory of this repository is a Node docs site. Its whole
pipeline is five steps:

```
docs/**.md          Markdown source
   │
   ├─ docmd build    ① read Markdown + docmd.config.js → site/
   │
   └─ site/          ② static HTML + search index + sitemap
        │
        └─ Actions  ③ push to main auto-publishes to GitHub Pages
```

Three files carry the whole thing, and you will use all of them today:

| File | Role | Go equivalent |
|------|------|----------------|
| `package.json` | Project declaration + dependency manifest + command aliases | `go.mod` + `Makefile` |
| `docmd.config.js` | Site config (src, out, theme, i18n) | `internal/config` + flag definitions |
| `tsconfig.json` | TypeScript compiler options | the compile-time constraints of `go build` |

---

## 1. Basic tech: a Node project = one package.json

The first visible difference between a Node project and a Go project is the
**entry point**:

| | Go | Node / TypeScript |
|---|-----|-------------------|
| Entry | `main.go` → `cmd.Execute()` | `package.json` `main` / `scripts` |
| Command definition | Cobra structs | the `scripts` field of `package.json` |
| Business code lives in | `internal/` (invisible outside) | `src/` (by convention + `exports`) |
| Dependency manifest | `go.mod` | `dependencies` in `package.json` |
| Dependency lock | `go.sum` | `package-lock.json` / `pnpm-lock.yaml` |
| Artifact | one binary | a pile of `.js` + `node_modules` (or a bundled file) |

### package.json field by field

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

| Field | Role | Notes |
|-------|------|-------|
| `name` / `version` | Project name and version | Anything for a private project |
| `private: true` | Prevent accidental npm publish | Always set it for a docs site |
| `type: "module"` | The whole project uses ESM syntax | Use `"commonjs"` for `require` |
| `scripts` | Command aliases | `npm run build` = `docmd build` |
| `dependencies` | Runtime dependencies | Shipped in the artifact |
| `devDependencies` | Development-only dependencies | Not shipped (typescript, eslint…) |

> **ESM vs CJS in one line**: modern Node defaults to ESM (`import` /
> `export`); older projects use CJS (`require` / `module.exports`). They can
> coexist: a `.cjs` extension forces CJS, `.mjs` forces ESM.

---

## 2. Using third-party packages

Node packages are also "wheels", downloaded from the npm registry.
**The package name is the feature you want**:

```bash
npm install @docmd/core          # a runtime dependency
npm install -D typescript @types/node   # dev dependencies (-D = --save-dev)
npm install docmd@latest         # a global CLI tool (not written to package.json)
```

After installing you get three things at once, and **all three are results —
do not edit them by hand**:

1. `node_modules/` — the packages themselves
2. `dependencies` in `package.json` — written automatically
3. `package-lock.json` — the lockfile, written automatically

### Using them from TypeScript

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

Three things worth remembering:

1. The **`node:` prefix** is the standard way to import Node built-ins
   (`node:fs`, `node:path`, …)
2. **Built-ins need types**: `npm i -D @types/node`, otherwise TypeScript
   reports "cannot find module"
3. **Types come from the package's `.d.ts`**: when a package ships its own
   types you do not install `@types/<pkg>`

### When no package fits

- npm keyword search: `cli` `parser` `markdown` `static site`
- Official docs: <https://docs.npmjs.com>
- If nothing fits, shell out with `child_process` — many Node packages are
  just thin wrappers around a CLI

---

## 3. Managing dependencies

| File | Role | Analogy (Go) |
|------|------|--------------|
| `package.json` | Declaration: name, version ranges, scripts | `go.mod` (but without checksums) |
| `package-lock.json` | **Exact version + hash** of every dependency | `go.sum` |
| `pnpm-lock.yaml` | pnpm's lockfile | same, different format |
| `node_modules/` | The installed packages | `GOMODCACHE` + vendor dir |

Common commands:

```bash
npm install            # install per package.json (creates/updates the lockfile)
npm ci                 # install strictly per the lockfile (CI preferred, always reproducible)
npm outdated           # which dependencies have newer versions
npm update <pkg>       # upgrade one dependency
npm uninstall <pkg>    # remove a dependency
npm audit              # check dependencies for known vulnerabilities
npm audit fix          # auto-fix what can be fixed
```

### Three good habits

1. **Commit `package.json` and the lockfile** — CI needs `npm ci` to
   reproduce your local build
2. **Separate dependencies from devDependencies** — build tooling such as
   `typescript` does not belong in runtime dependencies
3. **Use `npm ci` in CI, not `npm install`** — the former installs exactly
   the locked versions and never upgrades silently

### Which lockfile to pick

| Package manager | Lockfile | Traits |
|-----------------|----------|--------|
| npm | `package-lock.json` | Bundled, least friction |
| pnpm | `pnpm-lock.yaml` | Hard links from a shared store: less disk, faster installs |
| yarn | `yarn.lock` | The old guard of the ecosystem |

> Pick one, do not mix. This repository uses pnpm (see `pnpm-lock.yaml`);
> if your team standardizes on npm, use `npm install` + `package-lock.json`.

---

## 4. Build and toolchain

Node builds are looser than Go's — **there is no compile step by default**,
and the only thing that truly needs compiling is TypeScript.

### tsconfig.json: the compile rules in a file

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

| Option | Role | Advice |
|--------|------|--------|
| `target` | Which JS version to emit | `ES2022` |
| `module` / `moduleResolution` | Module syntax and resolution | `ESNext` + `bundler` |
| `outDir` / `rootDir` | Output dir / source dir | `dist` / `src` |
| `strict` | Turns on all strict checks | **always on** |
| `declaration` | Emits `.d.ts` declarations | only when publishing a package |
| `sourceMap` | Emits source maps | for debugging |

### npm scripts = the equivalent of a Makefile

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
npm run dev        # development (hot reload)
npm run typecheck  # type-check only, no output files
npm run build      # compile to dist/
npm test           # run tests
```

| Task | Node | Go |
|------|------|-----|
| Compile | `npm run build` (tsc) | `go build` |
| Check without emitting | `tsc --noEmit` | `go vet` |
| Run tests | `npm test` (vitest/jest) | `go test ./...` |
| Style | `eslint` + `prettier` | `gofmt` + `golangci-lint` |
| Task list | `scripts` in `package.json` | `Makefile` / `Taskfile.yml` |
| Cross-compile | usually unnecessary | `GOOS=windows go build` |

> A Node project rarely needs cross-compilation — the artifact is JS and
> runs everywhere. Reach for a bundler (`esbuild`, `pkg`,
> `node --experimental-sea`) only when you need a single executable file.

---

## 5. Use case: a TypeScript tool for the docs site

Now wire the knowledge together: **write a TypeScript tool that scans the
Markdown files under `docs/` and generates `navigation.json`**. Every docs
site eventually needs this.

### 5.1 Scaffold the project

```bash
mkdir docs-nav-tool && cd docs-nav-tool
npm init -y
npm i -D typescript @types/node tsx
npx tsc --init          # generate a tsconfig.json, then tune it
```

Layout:

```
docs-nav-tool/
├── package.json
├── tsconfig.json
└── src/
    └── nav.ts
```

### 5.2 Write the code

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

    // Title comes from the first h1, falling back to the file name
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

TypeScript-specific idioms worth picking up while you are here:

| Syntax | Meaning |
|--------|---------|
| `interface NavItem` | describes the shape of an object |
| `async` / `await` | asynchronous; `Promise<string[]>` means "will yield a string array" |
| `e.isDirectory()` | narrowing a directory entry type |
| `?.` / `??` | optional chaining / nullish coalescing |
| `const [, , srcDir = "docs/zh"]` | array destructuring with a default |

### 5.3 Wire it into scripts

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
npm run nav         # generate navigation.json
npm run typecheck   # type-check (run it before committing)
```

### 5.4 Wire it into CI

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

> `npm ci` + lockfile + `cache: npm` is the standard trio for a Node CI job.

---

## 6. Go vs Node in one table

| Dimension | Go | Node + TypeScript |
|-----------|-----|--------------------|
| Dependency manifest | `go.mod` | `package.json` |
| Lockfile | `go.sum` | `package-lock.json` / `pnpm-lock.yaml` |
| Install deps | `go mod download` | `npm ci` |
| Clean deps | `go mod tidy` | `npm prune` / delete and reinstall |
| Compile | `go build` | `tsc` |
| Type check | built into the compiler | `tsc --noEmit` |
| Task list | `Makefile` / `Taskfile.yml` | `scripts` in `package.json` |
| Artifact | one binary, cross-compile for platforms | `.js` files, portable by default |
| Distribution | `go install` / copy the binary | publish to npm, or `npm i -g` |

---

## Appendix A: Lesson prompt (paste into an AI assistant)

```text
You are my Node + TypeScript tutor. I am a complete beginner. Please teach
me with "write a navigation.json generator for a docs site" as the running
case, in four lessons, each with: a one-line concept, a runnable example,
and a small exercise.
1) Basic tech: what package.json / scripts / src/ each do; ESM vs CJS
2) Third-party packages: npm install, node: built-ins, @types packages
3) Dependency management: lockfiles, npm ci vs npm install, npm audit
4) Build and toolchain: tsconfig.json, tsc, eslint/prettier, npm ci in CI
Requirements: one lesson at a time; prefer real project files as examples;
exercises must be doable in 5 minutes; wait for my answer before the next
lesson.
```

## Appendix B: Skill (SKILL.md, installable as an agent skill)

Save as `SKILL.md` (e.g. `~/.codex/skills/nodejs-typescript-101/SKILL.md`
or `.claude/skills/nodejs-typescript-101/SKILL.md`) to expose it as a
"Node/TS lesson 1" skill:

```markdown
---
name: nodejs-typescript-101
description: Node.js + TypeScript essentials for absolute beginners. Use
  when the user wants to learn TypeScript tooling, understand
  package.json/tsconfig.json, or asks for "Node intro / TS intro / lesson 1".
---

# Node + TypeScript Essentials, Lesson 1

Use "a navigation.json generator for a docs site" as the running case and
teach four lessons in order, each with a 5-minute exercise:

1. **Basic tech** — `name`/`scripts`/`type` in `package.json`, ESM vs CJS;
   demonstrate `npm init -y` → `npm run dev`.
2. **Third-party packages** — `npm install` / `-D`; `node:` built-ins; why
   `@types/node` must be installed; read the `docs/` directory.
3. **Dependency management** — `package-lock.json` vs `pnpm-lock.yaml`;
   `npm ci` vs `npm install`; `npm audit`.
4. **Build and toolchain** — key `tsconfig.json` options, `tsc --noEmit`,
   npm scripts as a Makefile, `npm ci` in CI.

Teaching rules: one lesson at a time; explain in Chinese, keep code in
English; end each lesson with one exercise and wait for the answer; after
the last lesson offer three "go deeper" directions (unit tests, type-level
programming, bundling into a single file).
```

---

Next step: in your own docs-site project run `npm run nav && npm run
typecheck`, then hand `docs/` to docmd — that is your graduation project for
lesson 1.
