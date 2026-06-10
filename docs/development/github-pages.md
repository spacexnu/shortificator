# GitHub Pages Deploy

This repository includes a GitHub Actions workflow that builds MkDocs and deploys the generated site to GitHub Pages.

## Repository settings

In GitHub:

1. Open **Settings**.
2. Go to **Pages**.
3. Set **Build and deployment** to **GitHub Actions**.

## Workflow

The workflow runs on pushes to `main` and `master`, installs the Poetry `docs` dependency group, builds with:

```bash
poetry run mkdocs build --strict
```

Then it uploads `site/` as the Pages artifact and deploys it.

The published URL is expected to be:

```text
https://spacexnu.github.io/shortificator/
```
