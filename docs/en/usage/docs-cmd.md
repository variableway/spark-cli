# spark docs — Documentation Management

Manage the project documentation structure and the docmd site configuration.

## Quick Reference

```bash
spark docs init [--root <path>]               # Create the docs directory structure
spark docs site [--root <path>]               # Initialize the docmd site configuration
```

---

## spark docs init

Create the standard documentation directory structure:

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

| Flag | Default | Description |
|------|---------|-------------|
| `--root` | `.` | Project root directory |

```bash
spark docs init                               # Create in the current directory
spark docs init --root /path/to/project       # Create in a specific project
```

---

## spark docs site

Initialize a docmd site configuration:

- Auto-detect the project name and GitHub Pages URL from the git remote
- Generate `docmd.config.js` (sky theme, SPA layout, search/mermaid/llms plugins, i18n block)
- Install `@docmd/core` globally if docmd is not found
- Initialize `package.json` if it does not exist

| Flag | Default | Description |
|------|---------|-------------|
| `--root` | `.` | Project root directory |

```bash
spark docs site                               # Initialize in the current directory
spark docs site --root /path/to/project       # Initialize in a specific project
```

Once initialized:

```bash
docmd dev                                     # Local preview
docmd build                                   # Build the static site
```

## Related

- [Script Management](./script)
- [Task Management](./task)
