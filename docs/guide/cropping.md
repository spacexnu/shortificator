# Cropping Modes

Cropping controls how the 9:16 frame is chosen from the source video.

| Mode | Best for | Behavior |
| --- | --- | --- |
| `face` | talking-head video | uses YuNet and centers the crop on the main face |
| `gameplay` | game footage | stable center crop, no face detector |
| `center` | generic fallback | stable center crop |
| `auto` | conservative defaulting | currently follows the face-tracking path |

## Content mode

`--content-mode` changes the LLM prompt, not the crop itself.

| Mode | What the analysis looks for |
| --- | --- |
| `talking-head` | strong hooks, complete ideas, useful explanations |
| `gameplay` | tension, combat, pursuit, surprise, failure, victory, rare loot, player reaction |
| `auto` | generic selection guidance |

## Recommended combinations

```bash
--crop-mode face --content-mode talking-head
```

```bash
--crop-mode gameplay --content-mode gameplay
```

If you already know the content type, prefer an explicit mode over `auto`.
