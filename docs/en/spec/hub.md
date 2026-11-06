# spark hub — Command Spec

Project Hub command group. Scans local Git repositories and outputs registration information in the innate-apps registry format.

## Parent

```
spark hub
```

No arguments, no flags.

---

## spark hub scan

Scan the Git repositories in a directory (**top level by default**) and convert them into registry entries.

```
spark hub scan [path] [-o <file>] [--merge <file>] [--skip-api] [--deep] [--category <name>]
```

| Flag | Short | Type | Default | Required | Description |
|------|------|------|---------|----------|-------------|
| `--output` | `-o` | string | stdout | No | Output file path |
| `--merge` | | string | | No | Merge with an existing registry file, keeping manual fields |
| `--skip-api` | | bool | `false` | No | Skip the GitHub API, use local git information only |
| `--deep` | | bool | `false` | No | Include nested repositories (only the top level is scanned by default) |
| `--category` | | string | | No | Set the category for newly discovered entries |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `path` | string | No | Scan root directory, default `.` |

### Scan Behavior

- Find Git repositories with an `origin` remote (both `.git` directories and `.git` files); only the top level is taken by default, `--deep` removes the depth limit
- By default only **top-level** repositories are taken; `--deep` removes the depth limit
- Skip hidden directories as well as `node_modules` / `venv` / `.venv` / `__pycache__` / `dist` / `build`
- The remote URL must be in GitHub form (`https://github.com/<owner>/<repo>.git` or
  `git@github.com:<owner>/<repo>.git`) to enter the registry
- When `--skip-api` is true the GitHub API is not called and entries only contain fields inferable locally
- When an API call fails it **falls back automatically** to local information: the entry has no `language` and no
  `description`, while `visibility` stays `public`

Set `GITHUB_TOKEN` to raise the API rate limit.

### Output Format

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

| Field | Source |
|------|------|
| `$schema` | Fixed `./schema.json` |
| `version` | Fixed `1` |
| `updated_at` | Write date, format `2006-01-02` |
| `name` | GitHub repository name (the slug in the remote URL) |
| `title` | GitHub description; when empty, humanized from the directory name (`my-app` → `My App`) |
| `repo` | `owner/repo` parsed from `origin` |
| `url` | GitHub homepage; falls back to the repository URL when empty |
| `local_path` | Path relative to the scan root (always `/`-separated) |
| `category` | Defaults to `app`; `--category` overrides it |
| `status` | Defaults to `maintained` |
| `visibility` | GitHub API: `private` → `private`, otherwise `public` |
| `language` | GitHub API primary language |
| `description` | GitHub API description |

Category values: `base` / `app` / `reference`.
Status values: `maintained` / `archived` / `experimental`.

### Merge Behavior

When `--merge <file>` points at an existing registry file:

- **Manual fields are preserved**: `title`, `category`, `status`, `url`, `description`
- **Automatic fields are refreshed**: `repo`, `local_path`, `visibility`, `language`
- **Unmatched entries are preserved**: existing entries not found during the scan are kept as they are (for example the base frameworks under `../base/`)
- **New discoveries are appended**: newly scanned repositories are added automatically

Match order: first by `name`, then by `repo`.

### Output Location

- When both `-o` and `--merge` are given, the file specified by `-o` is written
- When only `--merge` is given, that file itself is written back
- When neither is given, the output goes to stdout

When a file is written, print `Wrote N collection(s) to <path>`.
