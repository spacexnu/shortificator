# Development

The project uses a flat package layout with `shortificator/` at the repository root.

Common commands:

```bash
make install
make check
make test
make cov
```

`make check` runs Ruff linting, Ruff format checking, and Python syntax compilation.

## Documentation

Install docs dependencies:

```bash
poetry install --only docs --no-root
```

Serve locally:

```bash
poetry run mkdocs serve
```

Build the static site:

```bash
poetry run mkdocs build --strict
```
