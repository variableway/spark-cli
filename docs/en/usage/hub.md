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

Output follows the innate-apps registry format (see `registry/schema.json` in the innate-apps repository for field definitions):

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
| `name` | GitHub repository name (the slug in the remote URL) |
| `title` | GitHub description (falling back to the humanized repo name, e.g. `my-app` -> `My App`) |
| `repo` | `owner/repo` parsed from git origin |
| `url` | GitHub homepage (or repo URL) |
| `local_path` | Path relative to the scan root |
| `category` | Default `app` (override with `--category`) |
| `status` | Default `maintained` |
| `visibility` | GitHub API (`private` → `private`, otherwise `public`) |
| `language` | GitHub API primary language |
| `description` | GitHub API description |

---

## spark hub scan

Scan a directory for git repositories (with an `origin` remote), fetch GitHub metadata via the API, and convert them into registry entries.

**Only the top level is scanned by default**; add `--deep` to include nested repositories.

```bash
spark hub scan /path/to/innate-apps
spark hub scan . -o registry/apps.json --merge registry/apps.json
```

| Option | Description |
|------|------|
| `-o, --output` | Output file path (default: stdout; with `--merge` and no `-o`, the result is written back to the merge file) |
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

Set the `GITHUB_TOKEN` environment variable to raise API rate limits. On API failure the scan falls back to local git info: `language` and `description` are empty, while `visibility` stays `public`.

---

## Relation to "getting the list of GitHub repository projects"

Three paths reach the same list of GitHub projects; they differ in the artifact:

| Path | Artifact | Use it for |
|------|----------|------------|
| `spark git update-org-status <account>` | A project-list section in a README | Pasting the list into a README or profile repo |
| `gh repo list` / `gh api` | The raw repository list | Rendering it yourself in any format |
| `spark hub scan` | Registry JSON with category and status | Maintaining a project hub site |

See [Git Management · How to get the list of GitHub repository projects](./git.md).

---

## Typical use: maintaining the innate-apps registry

`registry/apps.json` is the **data source** for innate-apps projects; the project
sections in READMEs and profile repositories are its **rendered output**. After
changing the data source, refresh the rendered output:

```bash
# 1. Scan inside the innate-apps directory and merge back into the registry
#    (keeps curated title/category/status)
spark hub scan . -o registry/apps.json --merge registry/apps.json

# 2. Commit, then refresh the downstream rendered output
#    - the innate-apps README project list
#    - the project section in the user profile repo qdriven/qdriven
#    - the project list in the org profile repo variableway/.github
spark git update-org-status variableway --update-dot-github
```

Field definitions live in `registry/schema.json`, conventions in
`registry/README.md`.
