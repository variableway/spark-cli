# spark hub — Project Hub (Collections Registration)

Scan local git repositories and produce innate-apps registry format (`registry/apps.json`) project registration info.

## Command Summary

```bash
spark hub scan <path>                              # Scan directory, print JSON to stdout
spark hub scan <path> -o registry/apps.json        # Write to a file
spark hub scan <path> --merge registry/apps.json   # Merge with an existing registry
spark hub scan <path> --skip-api                   # Skip GitHub API, use local info only
spark hub scan <path> --deep                       # Include nested repositories
spark hub scan <path> --category reference          # Set category
```

---

## Output Format

Output follows the innate-apps registry format (see `registry/schema.json` for field definitions):

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
| `name` | Directory name |
| `title` | GitHub description (or humanized directory name) |
| `repo` | `owner/repo` parsed from git origin |
| `url` | GitHub homepage (or repo URL) |
| `local_path` | Path relative to the scan root |
| `category` | Default `app` (override with `--category`) |
| `status` | Default `maintained` |
| `visibility` | GitHub API (`private` → `private`) |
| `language` | GitHub API primary language |
| `description` | GitHub API description |

---

## spark hub scan

Recursively scan a directory for git repositories (with an `origin` remote), fetch GitHub metadata via the API, and convert them into registry entries.

```bash
spark hub scan /path/to/innate-apps
spark hub scan . -o registry/apps.json --merge registry/apps.json
```

| Option | Description |
|------|------|
| `-o, --output` | Output file path (default: stdout) |
| `--merge` | Merge with an existing registry file, preserving curated fields |
| `--skip-api` | Skip GitHub API calls, use local git info only |
| `--deep` | Include nested repositories (default: top-level only) |
| `--category` | Set category for discovered entries (`base`/`app`/`reference`) |

### Merge Behavior

With `--merge`:

- **Preserves curated fields**: `title`, `category`, `status`, `url`, `description`
- **Refreshes auto fields**: `repo`, `local_path`, `visibility`, `language`
- **Keeps unmatched entries**: existing entries not found during the scan (e.g. base frameworks under `../base/`) are preserved as-is
- **Appends new discoveries**: newly scanned repositories are added

### GitHub API

Set the `GITHUB_TOKEN` environment variable to raise API rate limits. On API failure the scan falls back to local git info (without `language`/`description`/`visibility`).
