# Moved to spark hub

Scanning, listing, and cloning from a registry now live under [spark hub registry](./hub.md).

| Before | Now |
|--------|-----|
| `spark repo scan` | `spark hub registry scan` |
| `spark repo list` | `spark hub registry list` |
| `spark repo clone` | `spark hub registry clone` |
| `spark repo clone-registry` | `spark hub registry clone-registry` |

Apps you develop use `spark hub collections scan`. They are not written into the references registry.
