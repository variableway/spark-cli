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
- Re-scanning merges with the existing registry: matches by `path` first, then by `repo` URL, preserves old `name`/`desc`, keeps entries whose clone is absent locally verbatim (the registry doubles as a restore record for `repo clone -f`; removing an entry is a manual registry edit), and appends newly discovered repos

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
| `--depth` | int | `0` | No | Shallow clone depth (`git clone --depth=N`; 0 = full history) |

No arguments.

**Behavior**:
- Skips when `.git` already exists or the directory exists (`SKIP ...`)
- Runs `git clone <repo> <target>` for each repository
- Prints a `cloned / skipped / failed` summary; returns an error when `failed > 0`

---

## spark repo clone-registry

Clone only the repositories declared in a registry file whose target directory is missing on disk — the restore counterpart of `repo scan` keeping entries that are not checked out. The registry file is a positional argument.

```
spark repo clone-registry <registry-file> [--out <folder>] [--dry-run]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--out` | string | | No | Destination folder (default: derived from the registry file's location and name, `path/to/registry_<folder>.yaml` -> `path/to/<folder>/`) |
| `--dry-run` | bool | `false` | No | Print what would be cloned / skipped without cloning |
| `--depth` | int | `0` | No | Shallow clone depth (`git clone --depth=N`; 0 = full history) |

**Behavior**:
- Splits entries into on-disk / missing up front and prints an `N entries, N on disk, N missing` plan
- On-disk entries print `SKIP` and are counted, never re-cloned
- Missing entries run `git clone <repo> <target>` in ascending path-depth order
- `--dry-run` prints the `WOULD CLONE` list and returns immediately

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
