# spark docs — Command Spec

Documentation management command group.

## Parent

```
spark docs
```

No arguments, no flags.

---

## spark docs init

Create the standard documentation directory structure.

The generated structure:

```
docs/
├── analysis/
├── features/
├── index.md
├── quick-start/
├── README.md
├── spec/
├── tips/
└── usage/
```

Existing files and directories are skipped.

```
spark docs init [--root <path>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--root` | string | `.` | No | Project root directory |

No arguments.

---

## spark docs site

Initialize a docmd site configuration. Features:

- Auto-detect the project name and GitHub Pages URL from the git remote
- Generate `docmd.config.js` (sky theme, SPA layout, search/mermaid/llms plugins)
- Install `@docmd/core` globally if docmd is missing
- Initialize `package.json` if it does not exist

```
spark docs site [--root <path>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--root` | string | `.` | No | Project root directory |

No arguments.

After initialization:

```bash
docmd dev      # Local preview
docmd build    # Build the static site
```
