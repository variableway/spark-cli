# spark repo — Repository Management

Manage multiple GitHub repositories under a directory via a registry file, as an alternative to submodules.

## Quick Reference

```bash
spark repo scan [folder-name]                    # Scan a directory and write registry_<folder>.yaml
spark repo scan [folder-name] --json             # Also write a formatted registry_<folder>.json
spark repo scan [folder-name] --flatten          # Flatten directories deeper than two levels to category/repo before scanning
spark repo list -f registry_<folder>.yaml        # List repositories in the registry
spark repo clone -f registry_<folder>.yaml       # Clone every repository in the registry
spark repo clone -r <name> -f registry_<folder>.yaml  # Clone only the named repository
```

---

## spark repo scan

Recursively scan a directory, find Git repositories with an `origin` remote, and write them to `registry_<folder>.yaml` in the current directory.

```bash
spark repo scan                                # Scan the current directory
spark repo scan ~/workspace/innate-apps        # Scan a specific directory
spark repo scan ~/workspace/innate-apps --json # Also write registry_innate-apps.json
spark repo scan ~/workspace/innate-apps --flatten  # Flatten deep directories before scanning
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | `false` | Additionally write a formatted (2-space indent) `registry_<folder>.json` with the same content as the YAML |
| `--flatten` | `false` | Move repositories nested deeper than two levels (`category/repo`) up into the two-level layout before scanning |

**Flow**: (optional) `--flatten` deep directories → recursively locate `.git` (including `.git` files) → parse the `origin` remote URL → normalize → merge with the existing registry → write `registry_<folder>.yaml` (plus `registry_<folder>.json` when `--json` is set).

Scanning skips hidden directories and `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`. SSH URLs are normalized to HTTPS form. Re-scanning preserves existing `name`/`desc` and removes entries whose directory no longer exists.

### Two-level layout and --flatten

The directory layout follows a two-level convention: the first level is the category, the second level holds the actual repositories (`tooling/spark-cli`, `docs/quick-start`). When three or deeper levels exist, `--flatten` moves deep repositories up to `<category>/<repo-name>`, for example:

```
apps/fe/innate/web/innate-fe-cli  →  apps/innate-fe-cli
tooling/spark/spark-cli           →  tooling/spark-cli
```

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

---

## spark repo list

List the repositories in a registry file.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-f, --file` | | | Registry file (required) |

```bash
spark repo list -f registry_innate-apps.yaml
```

Each repository is printed as `name<TAB>repo<TAB>path`.

---

## Registry file

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

- [Git Management](./git)
