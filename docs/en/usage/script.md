# spark script — Script Management

Manage and run custom scripts.

## Quick Reference

```bash
spark script list                             # List every available script
spark script run <name> [args...]             # Run a script
```

---

## spark script list

List every available script. Scripts are sourced from two places:

1. The `spark.scripts` key in `~/.spark.yaml`
2. The `scripts/` directory at the project root

Entries from the config file take precedence.

```bash
spark script list
```

---

## spark script run

Run a named script, optionally passing arguments.

```bash
spark script run hello                        # Run the hello script
spark script run deploy prod                  # Pass arguments
spark script run copy-template my-feature     # Multiple arguments
```

## Config Example

Define scripts in `~/.spark.yaml`:

```yaml
spark:
  scripts:
    - name: hello
      content: |
        #!/bin/bash
        echo "Hello, $1!"
```

Or place executable files in the `scripts/` directory.

## Related

- [Task Management](./task)
- [Docs Management](./docs-cmd)
