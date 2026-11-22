# spark hub — Command Spec

Project hub. `registry` manages a references directory. `collections` registers apps you develop. The two outputs are not interchangeable.

## Parent

```
spark hub
```

```
spark hub registry
spark hub collections
```

No arguments and no flags.

---

## spark hub registry scan

Recursively scan a directory for git repositories with an `origin` remote and write `registry_<folder>.yaml` in the current directory.

```
spark hub registry scan [folder-name] [--json] [--flatten]
```

| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `folder-name` | string | `.` | No | Directory to scan |

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--json` | bool | `false` | No | Also write `registry_<folder>.json` |
| `--flatten` | bool | `false` | No | Legacy two-level layout only. Do not use on a three-level tree |

**Behavior**: skip hidden directories and `node_modules` / `venv` / `.venv` / `__pycache__` / `dist` / `build`. Store SSH URLs as HTTPS. Merge with an existing registry by `path`, then URL, keeping `name` / `desc` and any old entry whose checkout is absent. A folder with category directories is written as version 2 (`<category>/<subcategory>/others`). Otherwise the flat `projects:` format is used. A repository in the scan root prints WARNING and is omitted.

---

## spark hub registry list

```
spark hub registry list -f <registry-file>
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-f, --file` | string | | Yes | Registry file |

Categorized files print `# <category> / <subcategory> (n)`, then one `name<TAB>repo<TAB>path` row. An empty registry prints `No repositories in registry.`

---

## spark hub registry clone

```
spark hub registry clone [-r <name>] -f <registry-file> [--depth <n>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-f, --file` | string | | Yes | Registry file |
| `-r, --repo` | string | | No | Clone only this name |
| `--depth` | int | `0` | No | `git clone --depth=N`; 0 keeps full history |

The destination folder name is derived from `registry_<folder>.yaml` as `<folder>`. An existing `.git` or directory is SKIP. Clones run shallowest path first. A non-zero failure count returns an error.

---

## spark hub registry clone-registry

```
spark hub registry clone-registry <registry-file> [--out <folder>] [--dry-run] [--depth <n>]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `registry-file` | string | Yes | Registry file |

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--out` | string | derived from the file location and name | No | Destination directory |
| `--dry-run` | bool | `false` | No | Print `WOULD CLONE` only |
| `--depth` | int | `0` | No | Shallow clone depth |

Prints total / on disk / missing first. Entries already on disk are SKIP and are not cloned again.

---

## spark hub collections scan

Scan apps you develop and write an innate-apps collections catalog. Top level only by default.

```
spark hub collections scan [path] [-o <file>] [--merge <file>] [--skip-api] [--deep] [--category <name>]
```

| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `path` | string | `.` | No | Scan root |

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-o, --output` | string | stdout | No | Output file. With only `--merge`, that file is written back |
| `--merge` | string | | No | Merge an existing catalog and keep curated fields |
| `--skip-api` | bool | `false` | No | Do not call the GitHub API |
| `--deep` | bool | `false` | No | Include nested repositories |
| `--category` | string | | No | Category for new entries: `base` / `app` / `reference` |

Only GitHub remote URLs are recorded. A failed API call falls back to local git information. `--merge` matches `name`, then `repo`; it keeps `title` / `category` / `status` / `url` / `description`, refreshes `repo` / `local_path` / `visibility` / `language`, and keeps old entries that were not scanned.
