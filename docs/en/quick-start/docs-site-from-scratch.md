# Docs Site from Scratch and GitHub Pages Publishing

The other half of the beginner track: [Go CLI Project from
Scratch](golang-project-from-scratch.md) covers the binary; this tutorial
covers the **Node world** — starting with `npm init`, generating a docs site
with docmd, and auto-publishing to GitHub Pages via GitHub Actions. This very
site (the spark-cli docs) was built with exactly this flow.

You will walk away with:

1. A standard Node project with `package.json`
2. A docmd-powered Markdown docs site (previewable locally)
3. A GitHub Pages site that auto-deploys on every push to main
4. An installable SKILL document for AI assistants

---

## 0. Prerequisites

Install Node.js 20+ (<https://nodejs.org/>); npm ships with it, but
[pnpm](https://pnpm.io/) works too — both spellings are given below. Verify:

```bash
node -v     # v20.x or newer
npm -v
```

## 1. Step 1: `npm init` — where package.json comes from

A Node project likewise starts by **declaring itself**:

```bash
mkdir my-docs && cd my-docs
npm init -y
```

`-y` accepts all defaults. The generated `package.json`:

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

(That's the **final** state after installing dependencies; fresh
`npm init -y` only writes the first few fields.) Field by field:

| Field | Purpose | Notes |
|-------|---------|-------|
| `name` / `version` | Project name and version | Only matters when publishing to npm; private projects can be casual |
| `private: true` | Prevents accidental npm publishing | Always set this on a docs project |
| `type: "module"` | Use ES Module syntax project-wide | docmd's config uses `export default`, so this is required |
| `scripts` | Command aliases | `npm run build` = `docmd build`; turns long commands short |
| `dependencies` | Production dependency list | Written automatically by `npm install <pkg>` |

It maps one-to-one onto Go:

| Go | Node (this project) | Purpose |
|----|---------------------|---------|
| `go.mod` | `package.json` | Project + dependency declaration |
| `go.sum` | `package-lock.json` / `pnpm-lock.yaml` | Lock dependency versions |
| `go get <pkg>` | `npm install <pkg>` | Add a dependency |
| `go mod tidy` | `npm install` | Install what's declared |
| `go build` | `npm run build` | Produce artifacts |
| GOMODCACHE | `node_modules` (pnpm: hard links from a store) | Where dependencies live on disk |

## 2. Step 2: install docmd

[docmd](https://docmd.dev) is the generator behind this site: it reads
Markdown and emits static HTML with search, theme switching, i18n, mermaid,
and sitemap built in.

```bash
npm install @docmd/core @docmd/plugin-search @docmd/plugin-seo @docmd/plugin-sitemap
```

Three things happen: `node_modules/` appears, `package.json`'s `dependencies`
is updated, and the lockfile is written — **all three are results, don't edit
them by hand**.

Two more plugins spark uses (optional):

| Plugin | Purpose |
|--------|---------|
| `@docmd/plugin-llms` | Generates `llms.txt` so AI assistants can ingest the whole site |
| `@docmd/plugin-mermaid` | Renders Mermaid diagrams |

> pnpm users: just swap `npm install` for `pnpm add` / `pnpm install` —
> dependencies arrive as hard links from the global store (on Windows the store
> can live on D:, see [How to Build](../usage/how-to-build.md)).

## 3. Step 3: `docmd.config.js` — the site's master switch

Create `docmd.config.js` at the project root (trimmed from this repo's real
config):

```js
// docmd.config.js
export default defineConfig({
  title: 'My Docs',
  url: 'https://<you>.github.io/my-docs',   // Deploy URL; drives sitemap and SEO

  src: 'docs',       // Markdown source directory
  out: 'site',       // Build output directory (gitignore it)

  layout: {
    sidebar: { collapsible: true },         // Collapsible sidebar
  },
  theme: { name: 'sky' },                   // Built-in theme

  i18n: {
    default: 'en',                          // Default locale renders at the root URL
    locales: [
      { id: 'zh', label: '简体中文' },       // Other locale at /zh/
      { id: 'en', label: 'English' },
    ],
  },

  plugins: {
    search: {},                             // Matches the installed @docmd/plugin-search
    sitemap: { defaultChangefreq: 'weekly' },
  },
});
```

The key sections:

- **`src` / `out`**: input and output. `site/` is pure static files — safe to
  delete and rebuild at any time
- **`title` / `url`**: site metadata; `url` must match the final GitHub Pages
  address
- **`i18n`**: the `default` locale renders at the root URL, others mount under
  `/<locale>/`; one directory per locale (`docs/zh/`, `docs/en/`), each with
  its own `navigation.json` for the sidebar
- **`plugins`**: keys map to `@docmd/plugin-*` packages; `{}` enables defaults

## 4. Step 4: write your first page

```
docs/
├── zh/
│   ├── index.md             # Site home (the h1 becomes the page title)
│   ├── navigation.json      # Chinese sidebar
│   └── quick-start/
│       └── hello.md         # Your first page
└── en/                      # English mirror (structure must mirror zh/ exactly)
```

`docs/en/navigation.json`:

```json
[
  { "title": "Home", "path": "/" },
  {
    "title": "Quick Start",
    "icon": "rocket",
    "collapsible": true,
    "children": [
      { "title": "Hello", "path": "/quick-start/hello" }
    ]
  }
]
```

The body is plain Markdown; the page title is taken from the first `#`, no
front matter needed. The bilingual rule: **every new page exists in both
`zh/` and `en/`, and both `navigation.json` files register it** (if a
translation lags behind, docmd falls back to the default locale instead of
404ing).

## 5. Step 5: local development and build

```bash
npm run dev       # docmd dev: local dev server, Markdown edits hot-reload
npm run build     # docmd build: output into site/
npm run preview   # npx serve site: preview the static output like production
```

`site/` contains self-contained static HTML + search index + sitemap —
**add it to `.gitignore`** (build artifacts stay out of the repo; CI builds
them fresh).

## 6. Step 6: publish to GitHub Pages

The recommended way is "GitHub Actions + Pages artifact" — push to main
triggers a build and deploy. This repo's `.github/workflows/docs.yml` in full
(copy it as-is):

```yaml
name: Deploy Docs to GitHub Pages

on:
  push:
    branches: [main]
    paths:              # Only trigger when docs change, saves runner minutes
      - 'docs/**'
      - 'docmd.config.js'
  workflow_dispatch:    # Keep a manual trigger

permissions:
  contents: read
  pages: write          # Allow writing to Pages
  id-token: write       # OIDC deploy credential

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
        with: { path: site }      # Package site/ as a Pages artifact

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4   # Publish the artifact
```

Three steps to enable it:

1. Commit the workflow as `.github/workflows/docs.yml`
2. In the repo, **Settings → Pages → Build and deployment → Source**, choose
   **GitHub Actions** (not a branch — branch mode disables the Actions flow)
3. Push to main. Once Actions finishes, visit `https://<you>.github.io/my-docs/`

From then on, every change to `docs/**` or `docmd.config.js` merged into main
updates the site automatically — that's how this site ships.

> Manual publishing works too (not recommended): build locally with
> `npm run build`, push `site/` to a `gh-pages` branch, and point the Pages
> source at it. Downsides: easy to forget, easy to skip the lockfile.

## 7. Let spark do it for you

spark turned this tutorial's scaffolding into commands:

```bash
spark docs init    # Create the standard docs/ directory structure (usage/ spec/ features/ ...; skips existing)
spark docs site    # Detect title and Pages URL from the git remote, generate docmd.config.js,
                   # run npm init -y if package.json is missing, and install docmd deps
```

See the [Docs Management commands](../usage/docs-cmd.md).

---

## Appendix: SKILL — docs-site-from-scratch

Save as `SKILL.md` (e.g. `.claude/skills/docs-site-from-scratch/SKILL.md`)
and an AI assistant can build a docmd docs site and deploy it to GitHub Pages
for you:

```markdown
---
name: docs-site-from-scratch
description: Create a docmd docs site from scratch and publish it to GitHub
  Pages (npm init, package.json, docmd.config.js, navigation.json, bilingual
  i18n, Actions auto-deploy). Use when the user asks to "set up a docs site /
  create a docs project / publish docs to GitHub Pages".
---

# Docs Site from Scratch

Execute in this order, confirming with the user after each step:

1. **Project init** — npm init -y; package.json must contain "private": true
   and "type": "module" (docmd's config is ESM); explain scripts and
   dependencies.
2. **Install docmd** — npm install @docmd/core plus plugins as needed
   (search/seo/sitemap/llms/mermaid); remind that node_modules and the lockfile
   are install results, never hand-edited.
3. **Write docmd.config.js** — the src/out/title/url essentials; multiple
   languages via i18n.locales (default renders at the root URL, others at
   /<locale>/); plugin keys map to plugin packages.
4. **Organize docs** — docs/<locale>/ directories plus one navigation.json per
   locale; bodies are plain Markdown, titles come from the h1; in bilingual
   sites every new page is registered in both locales.
5. **Local verification** — npm run dev preview → npm run build into site/ →
   add site/ to .gitignore.
6. **Publish** — write .github/workflows/docs.yml (push to main + paths filter
   + upload-pages-artifact + deploy-pages, two jobs); set repo Settings →
   Pages → Source to GitHub Actions; push and verify.
   If the target repo has spark-cli installed, steps 3-4 can be replaced by
   spark docs init / spark docs site.

Reference implementation: github.com/variableway/spark-cli's docs/
(en mirror of a zh-default site); its docmd.config.js and
.github/workflows/docs.yml can be copied directly.
```

---

## Further reading

- [Go CLI Project from Scratch](golang-project-from-scratch.md) — the other half of this project: the Go world
- [How to Build](../usage/how-to-build.md) — Go vs Node build comparison, pnpm global config
- [Docs Management commands](../usage/docs-cmd.md) — `spark docs init` / `spark docs site`
