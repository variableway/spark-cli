# Skill Management

## Overview

`spark skill` discovers, lists, and syncs AI agent skills. A skill is simply **a directory
containing a `SKILL.md`** — the top of `SKILL.md` declares `name` and `description` in YAML
frontmatter, and the body holds the usage notes.

## Core Capabilities

### Multi-Location Discovery

One scan covers the three tiers of locations: project, global, and builtin:

```bash
spark skill list
```

| Tier | Location |
|------|------|
| Project | `.mimocode/skills/`, `.mimocode/skill/`, `.agents/skills/` |
| Global | `~/.claude/skills/`, `~/.agents/skills/`, `~/.mimocode/skills/`, `~/.mimocode/skill/` |
| Builtin | `~/.local/share/mimocode/builtin_skills/<version>/skills/` |

Only the highest-priority skill is kept when names collide: **project > global > builtin**; when
several builtin versions exist, the latest one is used.
The list shows each skill's source and full path.

### Structured Output

```bash
spark skill list --json
```

Outputs a JSON array (`name` / `description` / `path` / `source`) that can be piped straight into scripts.

### One-Command Aggregate Sync

Collect the skills scattered across locations into one directory, for centralized management or further editing:

```bash
spark skill sync ./skills            # Aggregate copy
spark skill sync ./skills --clear    # Clear the target directory first, then copy
```

After copying, the directory layout is `<target-dir>/<skill-name>/SKILL.md`.
`--clear` **deletes the existing contents of the target directory**, so make sure the target path is correct before running it.

## Parameters

| Command | Argument | Description |
|------|------|------|
| `list` | `[--json]` | List the discovered skills |
| `sync` | `<target-dir> [--clear]` | Copy all skills to the target directory |

## Typical Scenarios

| Scenario | Action |
|------|------|
| See which skills are installed locally | `spark skill list` |
| Export the project-level skills into a repository | `spark skill sync ./skills` |
| Copy the builtin skills into a project to modify them | `spark skill sync ./.agents/skills` |
| Verify that a skill is recognized | `spark skill list --json \| grep <name>` |

## Related

- [Skill Command Spec](../spec/skill.md)
- [Skill Usage Guide](../usage/skill.md)
