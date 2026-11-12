# spark skill — AI Skill Management

Find, list, and sync AI agent skills (`SKILL.md` directories).

## Command Summary

```bash
spark skill list                    # List all discovered skills
spark skill list --json             # JSON output
spark skill sync <target-dir>       # Copy all skills to the target directory
spark skill sync <target-dir> --clear  # Clear target, then copy
```

---

## Skill Discovery Locations

`spark skill` scans these well-known locations for directories containing `SKILL.md`:

| Location | Source label |
|----------|----------|
| `.mimocode/skills/`, `.mimocode/skill/` (current project) | `project` |
| `.agents/skills/` (current project) | `project` |
| `~/.claude/skills/` | `claude` |
| `~/.agents/skills/`, `~/.mimocode/skills/`, `~/.mimocode/skill/` | `global` |
| `~/.local/share/mimocode/builtin_skills/<version>/skills/` | `builtin:<version>` |

Skills are deduplicated by name: project-level wins over global, global wins over builtin; for builtin skills the newest version wins.

---

## spark skill list

Scan all locations and list discovered skills.

```bash
spark skill list
spark skill list --json
```

Output includes skill name, source, and path. `--json` emits structured JSON for scripting.

The `name` and `description` fields are parsed from the SKILL.md YAML frontmatter; the directory name is used as fallback.

---

## spark skill sync

Copy all discovered skills to a target directory.

```bash
spark skill sync ./skills               # Copy to ./skills
spark skill sync ./skills --clear       # Clear ./skills first, then copy
spark skill sync ~/.claude/skills       # Sync into Claude skills directory
```

| Option | Description |
|------|------|
| `--clear` | Clear the target directory before copying |

Typical use: consolidate skills scattered across locations into one directory (e.g. the `fire-skills` repo), or copy builtin skills into a project for local customization.
