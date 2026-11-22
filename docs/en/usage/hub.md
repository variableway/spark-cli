# spark hub — Project Hub

`spark hub` has two paths. They are not interchangeable.

| Path | What it manages | Output |
|------|-----------------|--------|
| `registry` | Reference repositories, cloned back from the list | `registry_<folder>.yaml` |
| `collections` | Registration of apps you develop | `registry/apps.json` |

A directory of repositories is tracked with registry, not with git submodules.

## Command Summary

```bash
# references
spark hub registry scan [folder-name]
spark hub registry scan [folder-name] --json
spark hub registry list -f registry_<folder>.yaml
spark hub registry clone -f registry_<folder>.yaml
spark hub registry clone -r <name> -f registry_<folder>.yaml
spark hub registry clone-registry <registry-file>

# apps you develop
spark hub collections scan [path]
spark hub collections scan . -o registry/apps.json --merge registry/apps.json
```

---

## spark hub registry

Manages a references directory. Scan writes git repositories that have an `origin` remote to `registry_<folder>.yaml` in the current directory. `list` prints the file. `clone` and `clone-registry` clone each entry to its recorded `path`.

The directory layout is three levels: `<category>/<subcategory>/<project>`. Categories are the folder's immediate subdirectories (empty ones are still recorded), and every category has an `others` subcategory. A project sitting directly under a category is filed under `others`. A folder with no category directories keeps the legacy flat `projects:` format. A repository sitting in the scan root prints `WARNING` and is not written.

```bash
spark hub registry scan ~/workspace/innate-references
spark hub registry scan ~/workspace/innate-references --json
spark hub registry list -f registry_innate-references.yaml
spark hub registry clone -f registry_innate-references.yaml
spark hub registry clone-registry ~/innate/base/innate-skills/registry_references.yaml --dry-run
```

| Command | Flag | Description |
|---------|------|-------------|
| `scan` | `--json` | Also write a formatted `registry_<folder>.json` |
| `scan` | `--flatten` | Legacy two-level layout only: move repos deeper than two levels up before scanning. Do not use this on a three-level tree |
| `list` | `-f, --file` | Registry file (required) |
| `clone` | `-f, --file` | Registry file (required) |
| `clone` | `-r, --repo` | Clone only the named repository |
| `clone` | `--depth` | Shallow clone depth; `0` keeps full history |
| `clone-registry` | `--out` | Destination directory. Default is derived from the registry file's location and name |
| `clone-registry` | `--dry-run` | Print the plan only |
| `clone-registry` | `--depth` | Shallow clone depth; `0` keeps full history |

Re-scanning merges with the existing registry: match by `path`, then by repository URL, and keep `name` / `desc`. Entries whose checkout is absent stay in the file, so the registry is also the restore record. Removing an entry is a manual edit.

`clone` derives the destination folder from the file name (`registry_<folder>.yaml` → `<folder>`) and skips directories that already exist. `clone-registry` clones only entries missing on disk. Its default destination is next to the registry file.

Scanning skips hidden directories and `node_modules` / `venv` / `.venv` / `__pycache__` / `dist` / `build`. SSH URLs are stored as HTTPS.

### Registry file

```yaml
# Project registry
# Synced by spark hub registry scan

version: 2
categories:
  - name: skills
    subcategories:
      - name: agent
        projects:
          - name: taste-skill
            repo: https://github.com/Leonxlnx/taste-skill.git
            path: skills/agent/taste-skill
      - name: others
        projects: []
```

---

## spark hub collections scan

Registers apps you develop. It scans local git repositories, fills description, language, and visibility from the GitHub API, and writes an innate-apps collections catalog.

Only the top level is scanned unless `--deep` is set.

```bash
spark hub collections scan /path/to/innate-apps
spark hub collections scan . -o registry/apps.json --merge registry/apps.json
spark hub collections scan . --skip-api --category app
```

| Flag | Description |
|------|-------------|
| `-o, --output` | Output file. Default is stdout; with only `--merge`, the file is written back in place |
| `--merge` | Merge with an existing catalog and keep curated fields |
| `--skip-api` | Do not call the GitHub API |
| `--deep` | Include nested repositories |
| `--category` | Category for new entries: `base` / `app` / `reference` |

`--merge` keeps `title`, `category`, `status`, `url`, and `description`, and refreshes `repo`, `local_path`, `visibility`, and `language`. Entries that were not seen in this scan stay as they are. `GITHUB_TOKEN` raises the API rate limit.

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

After editing `registry/apps.json`, refresh README and profile project lists with `spark git update-org-status`. Field definitions are in `registry/schema.json`.
