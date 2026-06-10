# Testing

Run the lightweight local gate:

```bash
make check
```

Run the test suite:

```bash
make test
```

Write coverage reports:

```bash
make cov
```

The unit suite should focus on pure logic and mock external boundaries. Real render/transcription checks need video files, CUDA, FFmpeg, and Ollama, so they are better treated as manual or integration runs.
