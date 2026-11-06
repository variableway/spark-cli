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

---

## The spark-cli skill shipped with this repository

`skills/spark-cli/SKILL.md` is a skill that ships with this repository. It is
the **agent-facing version of this usage guide**: the command map, the common
workflows, and the three paths for fetching the list of GitHub repository
projects. Install it into your agent's skill directory and the assistant knows
how to drive spark:

```bash
# Install from this repository into Claude's skills directory
spark skill sync ~/.claude/skills --clear

# Or install just this one
mkdir -p ~/.claude/skills/spark-cli
cp skills/spark-cli/SKILL.md ~/.claude/skills/spark-cli/
```

Afterwards `spark skill list` shows it:

```text
NAME                   SOURCE           PATH
spark-cli              claude           /Users/me/.claude/skills/spark-cli
```

> Skill directory convention: each skill is a **directory** holding a
> `SKILL.md`; the `name` and `description` in its frontmatter decide when the
> assistant picks it up.
