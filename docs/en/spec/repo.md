# spark repo — Command Spec

Manage multiple GitHub repositories under a directory via a registry file (not submodules).

## Parent

```
spark repo
```

No arguments, no flags.

Registry file format:

```yaml
# Project registry
# Synced by spark repo scan

projects:
    - name: spark-cli
      repo: https://github.com/variableway/spark-cli.git
      path: tooling/spark-cli
      desc: Spark CLI tool
```

---

## spark repo scan

Recursively scan a directory for Git repositories (only those with an `origin` remote) and write them to `registry_<folder>.yaml` in the current directory.

```
spark repo scan [folder-name]
```

| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `folder-name` | string | `.` | No | Directory to scan |

No flags.

**Behavior**:
- Recursively locates `.git` directories and `.git` files (including `gitdir:` redirection), parsing the `url` under `[remote "origin"]`
- Skips hidden directories and `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`
- SSH URLs are normalized to HTTPS form before being stored
- The registry file name uses the base name of the directory's absolute path: `registry_<folder>.yaml`
- Re-scanning merges with the existing registry: matches by `path` first, then by `repo` URL, preserves old `name`/`desc`, drops entries whose directory no longer exists, and appends newly discovered repos

---

## spark repo clone

Clone repositories from a registry file into the folder directory. The target folder name is derived from the registry file name (`registry_<folder>.yaml` → `<folder>`).

```
spark repo clone [-r <repo-name>] -f <registry-file>
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-r, --repo` | string | | No | Clone only the named repository (omit to clone all) |
| `-f, --file` | string | | Yes | Registry file (`registry_<folder>.yaml`) |

No arguments.

**Behavior**:
- Skips when `.git` already exists or the directory exists (`SKIP ...`)
- Runs `git clone <repo> <target>` for each repository
- Prints a `cloned / skipped / failed` summary; returns an error when `failed > 0`

---

## spark repo list

List the repositories declared in a registry file (name, remote URL and relative path).

```
spark repo list -f <registry-file>
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-f, --file` | string | | Yes | Registry file (`registry_<folder>.yaml`) |

No arguments.

**Output**: one `name<TAB>repo<TAB>path` line per repository; prints `No repositories in registry.` when empty.
