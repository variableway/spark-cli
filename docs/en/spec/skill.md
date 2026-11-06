# spark skill — Command Spec

AI Skill management command group. Used to discover, list, and sync `SKILL.md` directories.

## Parent

```
spark skill
```

No arguments, no flags.

---

## spark skill list

Scan all known locations and list the discovered skills.

```
spark skill list [--json]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--json` | bool | `false` | No | Output as JSON, easy to consume from scripts |

No arguments.

### Discovery Locations and Source Labels

Scanned in the following order; the source label is the `source` column in the list:

| Order | Location | `source` |
|------|------|----------|
| 1 | `<cwd>/.mimocode/skills/` | `project` |
| 2 | `<cwd>/.mimocode/skill/` | `project` |
| 3 | `<cwd>/.agents/skills/` | `project` |
| 4 | `~/.claude/skills/` | `claude` |
| 5 | `~/.agents/skills/` | `global` |
| 6 | `~/.mimocode/skills/` | `global` |
| 7 | `~/.mimocode/skill/` | `global` |
| 8 | `~/.local/share/mimocode/builtin_skills/<version>/skills/` | `builtin:<version>` |

- Each first-level subdirectory is one skill and must contain a `SKILL.md`
- The builtin directories are scanned in descending version order; when several versions exist, **the latest version wins**
- **Duplicate names are deduplicated**: the first one wins, so the scan order is the priority order (project > global > builtin)
- Missing directories are skipped without an error

### Name and Description Parsing

Reads the YAML frontmatter of `SKILL.md`:

- `name`: falls back to the directory name
- `description`: may be omitted

### Output

Text output is a three-column table (`NAME` / `SOURCE` / `PATH`); long descriptions are truncated to 60 characters.
When no skill is found at all, print `No skills found.` and list the search locations.

`--json` outputs a JSON array:

```json
[
  {
    "name": "spark-cli",
    "description": "Usage guide for the spark command-line tool",
    "path": "/Users/me/.claude/skills/spark-cli",
    "source": "claude"
  }
]
```

---

## spark skill sync

Copy the discovered skills to the target directory.

```
spark skill sync <target-dir> [--clear]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--clear` | bool | `false` | No | Clear the target directory before copying |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `target-dir` | string | Yes | Target directory |

Behavior:

1. Scan and deduplicate (same as `list`)
2. When no skill is found at all, print `No skills found to sync.` and return immediately, without creating the directory
3. With `--clear`, clear the target directory first
4. Each skill is copied to `<target-dir>/<skill-name>/`
5. Afterwards, print the number of copies and each target path

When no skill was copied, the target directory may not have been created yet.
