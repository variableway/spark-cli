# spark script — Command Spec

Custom script management command group.

## Parent

```
spark script
```

No arguments, no flags.

---

## spark script list

List every available script. Sources:

- The `spark.scripts` (or top-level `scripts`) key in `~/.spark.yaml`
- Executable files under the project's `scripts/` directory

```
spark script list
```

No flags, no arguments.

---

## spark script run

Run a named script.

```
spark script run <script-name> [args...]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `script-name` | string | Yes | Script name |
| `args` | string[] | No | Arguments forwarded to the script |

No flags.
