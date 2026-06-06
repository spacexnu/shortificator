# Contributing to shortificator

Thanks for your interest in improving **shortificator**! This document describes
how to set up the project locally and the conventions to follow when submitting
changes.

## Getting started

1. **Fork** the repository.
2. **Clone** your fork and create a feature branch:

   ```bash
   git clone https://github.com/<your-username>/shortificator.git
   cd shortificator
   git checkout -b my-new-feature
   ```

3. **Install** the dependencies (see the [README](README.md#requirements) for the
   system-level prerequisites — Python 3.13+, Poetry, FFmpeg, CUDA, Ollama):

   ```bash
   poetry install
   ```

4. Verify your environment:

   ```bash
   make check-env
   ```

## Development workflow

1. Make your change.
2. Add or update tests for any new behavior.
3. Run the full local check before committing:

   ```bash
   make check   # ruff lint + format check + syntax check
   make test    # run the test suite with coverage
   ```

4. **Commit** your changes with a clear message:

   ```bash
   git commit -am "Add my new feature"
   ```

5. **Push** the branch to your fork:

   ```bash
   git push origin my-new-feature
   ```

6. **Open a pull request** against the `main` branch and describe what you changed
   and why. Link any related issue.

## Coding guidelines

- **Language:** all identifiers (modules, classes, functions, variables) and code
  comments must be written in **English**.
- **Comments:** keep them minimal — add a comment only when it explains a
  non-obvious decision, not what the code already says.
- **Type hints** are expected on public functions.
- **Style & formatting** are enforced by [ruff](https://docs.astral.sh/ruff/).
  Run `make fmt` to format and `make lint-fix` to auto-fix lint issues. CI will
  reject changes that do not pass `make check`.
- **Module boundaries:** keep pure logic (data models, selection heuristics,
  prompts, subtitle timing/styling) free of heavy runtime dependencies
  (`torch`, `ultralytics`, `faster_whisper`, `ollama`, `cv2`). Import those lazily
  inside the functions that need them so the package stays fast to import and
  testable without a GPU.
- **Progress output:** use `print` for orchestration-level progress only; utility
  functions should stay quiet.
- **Subprocesses:** call FFmpeg/FFprobe via `subprocess.run`, never `os.system`.

## Tests

The unit suite lives in `tests/` and runs without a GPU, models, or network by
mocking the external boundaries (Ollama, FFmpeg, the rendering stages):

```bash
make test          # run the suite (prints a coverage summary)
make cov           # also write coverage.xml and htmlcov/index.html
```

When adding a feature, prefer extending the pure-logic modules so the new code is
straightforward to cover with fast unit tests. Heavy I/O paths (frame rendering,
YOLO cropping, transcription, download) are validated manually or via integration
runs rather than the unit suite.

## Reporting issues

When opening an issue, please include:

- what you expected to happen and what actually happened;
- the exact command you ran;
- relevant environment details (OS, Python version, GPU/CUDA, Ollama model);
- any error output or stack trace.
