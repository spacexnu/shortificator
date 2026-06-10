# Subtitles

Subtitles are burned into the video frames with Pillow and OpenCV.

Pillow handles TrueType fonts and UTF-8 correctly, so accented text renders properly. OpenCV's default Hershey fonts are ASCII-only and are not used for final subtitle text.

## Static subtitles

The default subtitle path uses a sliding word window centered on the current word.

## Dynamic subtitles

Enable the dynamic style with:

```bash
--dynamic-subtitles
```

Dynamic subtitles use fixed word blocks. The block stays in place while the current word is highlighted. When speech crosses into the next group, the block advances.

## Style flags

| Flag | Default | Description |
| --- | --- | --- |
| `--sub-font` | auto-detected | path to a `.ttf` font |
| `--sub-font-size` | `78` | starting font size in pixels |
| `--sub-color` | `255,255,255` | normal word color |
| `--sub-highlight-color` | `255,224,64` | current word color |
| `--sub-stroke-color` | `0,0,0` | outline color |
| `--sub-stroke-width` | `5` | outline width |
| `--sub-y-ratio` | `0.74` | vertical position |
| `--sub-max-lines` | `2` | maximum subtitle lines |
| `--sub-words-per-chunk` | `4` | words per dynamic block |
| `--sub-no-uppercase` | off | preserve original casing |

Colors accept `R,G,B` or `#RRGGBB`.
