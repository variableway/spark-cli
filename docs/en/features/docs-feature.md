# Documentation Management

## Overview

`spark docs` manages the project documentation structure and the docmd site configuration. With one command it creates the standard docs layout and generates the docmd config file.

## Core Capabilities

### Docs Directory Initialization

Create the standard documentation layout:

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

Existing files and directories are skipped and never overwritten.

```bash
spark docs init
spark docs init --root /path/to/project
```

### docmd Site Initialization

Automatically generate the docmd config file `docmd.config.js`:

- Auto-detect the project name and GitHub Pages URL from the git remote
- Configure the sky theme and SPA layout
- Enable the search, Mermaid, and LLM full-text index plugins
- Install `@docmd/core` if missing
- Initialize `package.json` if missing

```bash
spark docs site
spark docs site --root /path/to/project
```

After initialization:

```bash
docmd dev      # Local preview
docmd build    # Build the static site
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--root` | string | `.` | Project root directory |

## Dependencies

- Node.js (for the docmd site feature)
- `@docmd/core` (installed automatically)

## Related

- [Docs Command Spec](/en/spec/docs-cmd)
- [Docs Usage Guide](/en/usage/docs-cmd)
