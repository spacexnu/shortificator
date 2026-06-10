# Project Layout

```text
shortificator/
├── shorts_factory.py
├── pyproject.toml
├── Makefile
├── README.md
├── CONTRIBUTING.md
├── mkdocs.yml
├── docs/
└── shortificator/
    ├── cli.py
    ├── config.py
    ├── pipeline.py
    ├── transcription.py
    ├── download.py
    ├── media.py
    ├── analysis/
    ├── subtitles/
    └── rendering/
```

Pure modules avoid heavy imports so they stay quick to import and easy to test:

- `config`
- `models`
- `analysis.selection`
- `analysis.prompts`
- `subtitles.style`
- `subtitles.timing`

Heavy dependencies such as OpenCV, faster-whisper, Ollama, and FFmpeg process calls are isolated behind runtime functions.
