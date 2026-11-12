# spark repo — Repository Management

Manage multiple GitHub repositories under a directory via a registry file, as an alternative to submodules.

## Quick Reference

```bash
spark repo scan [folder-name]                    # Scan a categorized directory and write registry_<folder>.yaml
spark repo scan [folder-name] --json             # Also write a formatted registry_<folder>.json
spark repo scan [folder-name] --flatten          # (legacy two-level layout only) flatten to category/repo before scanning
spark repo list -f registry_<folder>.yaml        # List repositories (grouped output for categorized registries)
spark repo clone -f registry_<folder>.yaml       # Clone every repository to its recorded path
spark repo clone -r <name> -f registry_<folder>.yaml  # Clone only the named repository
```

---

## spark repo scan

Recursively scan a directory, find Git repositories with an `origin` remote, and write them to `registry_<folder>.yaml` in the current directory (categorized format).

```bash
spark repo scan                                # Scan the current directory
spark repo scan ~/workspace/innate-references  # Scan a specific directory (three-level layout)
spark repo scan ~/workspace/innate-apps --json # Also write registry_innate-apps.json
spark repo scan ~/workspace/legacy-refs --flatten  # Legacy two-level layout: flatten first
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | `false` | Additionally write a formatted (2-space indent) `registry_<folder>.json` with the same content as the YAML |
| `--flatten` | `false` | Move repositories nested deeper than two levels (`category/repo`) up into the **legacy** two-level layout before scanning; do not use it on a `category/subcategory/project` tree |

**Flow**: (optional) `--flatten` deep directories → recursively locate `.git` (including `.git` files) → parse the `origin` remote URL → normalize → merge with the existing registry → group by category (`Categorize`) → write `registry_<folder>.yaml` (plus `registry_<folder>.json` when `--json` is set).

Scanning skips hidden directories and `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`. SSH URLs are normalized to HTTPS form. Re-scanning preserves existing `name`/`desc` and removes entries whose directory no longer exists.

### Three-level categorized layout (registry v2)

The directory layout follows a three-level convention: `<category>/<subcategory>/<project>`.

```
references/
├── skills/                 # level 1 = category (directory name becomes the registry category)
│   ├── agent/              # level 2 = subcategory
│   │   └── taste-skill/    # level 3 = project (a git repo with an origin remote)
│   └── others/             # projects without a subcategory go to others (always present)
├── products/
│   └── others/
└── plugins/
    └── others/
```

- **Categories** are the folder's immediate subdirectories (they appear even when they hold no projects); **every category always contains an `others` subcategory**.
- A project directly under a category (`skills/some-project`) has no subcategory and is recorded under that category's `others` (move it on disk to `skills/others/some-project`).
- Repositories nested deeper inside a project (e.g. `fire-skills/downloads/*`) keep their full path but are grouped by their first two segments.
- A repository directly under the scan root has no category: a `WARNING` is printed and it is not written to the registry (move it into a category first).
- A directory **without any category subdirectories** automatically falls back to the legacy flat `projects:` format, exactly as before.

### `--flatten` is for the legacy two-level layout only

The legacy convention is two levels: the first is the category, the second holds the repositories (`tooling/spark-cli`). When three or deeper levels exist, `--flatten` moves deep repositories up to `<category>/<repo-name>`, for example:

```
apps/fe/innate/web/innate-fe-cli  →  apps/innate-fe-cli
tooling/spark/spark-cli           →  tooling/spark-cli
```

- **Do not run `--flatten` on a three-level categorized tree**: it would move `skills/agent/taste-skill` up to `skills/taste-skill`, destroying the subcategory. The categorized layout is grouped by `Categorize` and moves nothing.
- Nothing is overwritten: when the target already exists (or was claimed by another repository in the same run), the repository stays in place and a `Skipped ...` warning is printed.
- Empty intermediate directories are removed after a move.
- `--flatten` modifies the directory structure on disk and is destructive; confirm before using it.

---

## spark repo clone

Clone repositories from a registry file into the folder directory. The target folder name is derived from the registry file name (`registry_<folder>.yaml` → `<folder>`).

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-r, --repo` | | | Clone only the named repository |
| `-f, --file` | | | Registry file (required) |

```bash
# Clone every repository in the registry into the innate-apps directory
spark repo clone -f registry_innate-apps.yaml

# Clone only the named repository
spark repo clone -r spark-cli -f registry_innate-apps.yaml
```

Repositories that already exist (`.git` present or directory exists) are skipped; a `cloned / skipped / failed` summary is printed at the end.

Destinations restore the `path` recorded in the registry (for a categorized registry that is `<category>/<subcategory>/<project>`), cloned **shallowest path first** so a parent project exists before any nested clone recorded under it.

---

## spark repo list

List the repositories in a registry file.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-f, --file` | | | Registry file (required) |

```bash
spark repo list -f registry_innate-apps.yaml
```

Each repository is printed as `name<TAB>repo<TAB>path`. For categorized (v2) registries a group header `# <category> / <subcategory> (<count>)` is printed before each bucket (rows stay machine-readable; filter lines starting with `#`).

---

## Registry file

**Categorized format (v2 — the default output when scanning a three-level tree)**:

```yaml
# Project registry
# Synced by spark repo scan

version: 2
categories:
    - name: skills
      subcategories:
        - name: agent
          projects:
            - name: taste-skill
              repo: https://github.com/Leonxlnx/taste-skill.git
              path: skills/agent/taste-skill
              desc: Frontend taste skill
        - name: others
          projects: []
    - name: products
      subcategories:
        - name: others
          projects: []
    - name: plugins
      subcategories:
        - name: others
          projects: []
```

**Legacy flat format (still written and read for directories without category subdirectories)**:

```yaml
# Project registry
# Synced by spark repo scan

projects:
    - name: spark-cli
      repo: https://github.com/variableway/spark-cli.git
      path: tooling/spark-cli
      desc: Spark CLI tool
```

## Related

- [Git Management](./git.md)
