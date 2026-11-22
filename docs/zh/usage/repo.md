# 已并入 spark hub

仓库扫描、清单和按 registry 克隆已并入 [spark hub registry](./hub.md)。

| 以前 | 现在 |
|------|------|
| `spark repo scan` | `spark hub registry scan` |
| `spark repo list` | `spark hub registry list` |
| `spark repo clone` | `spark hub registry clone` |
| `spark repo clone-registry` | `spark hub registry clone-registry` |

自己开发的 app 用 `spark hub collections scan`，不写进 references registry。
