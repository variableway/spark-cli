# Project Hub

## Overview

`spark hub` turns a pile of local Git repositories into a **project registry** — a JSON project
manifest listing who each project is, its address on GitHub, its category, status, visibility, and
primary language. It replaces managing multiple projects with git submodules: the registry is a
**data file** that can be versioned, reviewed, and consumed by the docs site.

## Core Capabilities

### Scan Local Repositories to Build a Registry

```bash
spark hub scan .
spark hub scan . -o registry/apps.json
```

The scan finds Git repositories with an `origin` remote, calls the GitHub API to fill in
description / language / visibility, then outputs the innate-apps registry format (see
`registry/schema.json` for the field definitions).

By default only the top-level directory is scanned; `--deep` includes nested repositories.

### Keep Manually Maintained Fields When Merging

```bash
spark hub scan . -o registry/apps.json --merge registry/apps.json
```

| Field | Merge Strategy |
|------|----------|
| `title` / `category` / `status` / `url` / `description` | **Preserve** the manual values from the existing registry file |
| `repo` / `local_path` / `visibility` / `language` | **Refresh** from the current scan result |
| Entries that were not scanned | Preserved as they are (e.g. the base frameworks under `../base/`) |
| Newly scanned repositories | Appended to the list |

### Offline Mode

```bash
spark hub scan . --skip-api
```

Does not call the GitHub API and derives the entries from local git information only; when an API
call fails it also falls back automatically to local information (the entry carries no
`language` / `description`).

## Parameters

| Command | Argument | Description |
|------|------|------|
| `scan` | `[path]` | Scan root directory, default `.` |
| `scan` | `-o, --output <file>` | Output file, default stdout |
| `scan` | `--merge <file>` | Merge with an existing registry file |
| `scan` | `--skip-api` | Skip the GitHub API |
| `scan` | `--deep` | Include nested repositories |
| `scan` | `--category <name>` | Set the category: `base` / `app` / `reference` |

## Output Structure

```json
{
  "$schema": "./schema.json",
  "version": 1,
  "updated_at": "2026-11-01",
  "collections": [
    {
      "name": "spark-cli",
      "title": "Spark CLI",
      "repo": "variableway/spark-cli",
      "url": "https://github.com/variableway/spark-cli",
      "local_path": "spark-cli",
      "category": "app",
      "status": "maintained",
      "visibility": "public",
      "language": "Go",
      "description": "Daily Cli command ideas fired by spark"
    }
  ]
}
```

Category: `base` (base framework) / `app` (application) / `reference` (reference project).
Status: `maintained` / `archived` / `experimental`.

## Downstream: Registry → Docs and Profile

The registry is the **data source**; the project lists in the README and in profile repositories
are its **rendered output**. After editing `apps.json`, refresh them in sync:

1. The aggregate repository's own README project list
2. The project section in a user profile repository (e.g. `qdriven/qdriven`)
3. The project section in an organization profile repository (e.g. `<org>/.github`)

`spark git update-org-status <org>` handles the third kind (writing the GitHub repository list into
the README section, sorted by star count); the first two are usually rendered by hand from the
registry contents.

## Related

- [Hub Command Spec](../spec/hub.md)
- [Hub Usage Guide](../usage/hub.md)
- [Git Management](../features/git.md)
