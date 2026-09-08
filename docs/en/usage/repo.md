# spark repo — Repository Management

Manage multiple GitHub repositories under a directory via a registry file, as an alternative to submodules.

## Quick Reference

```bash
spark repo scan [folder-name]                    # Scan a directory and write registry_<folder>.yaml
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
```

**Flow**: recursively locate `.git` (including `.git` files) → parse the `origin` remote URL → normalize → merge with the existing registry → write `registry_<folder>.yaml`.

Scanning skips hidden directories and `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`. SSH URLs are normalized to HTTPS form. Re-scanning preserves existing `name`/`desc` and removes entries whose directory no longer exists.

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
