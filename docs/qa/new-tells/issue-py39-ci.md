The `test (3.9)` job in `ci.yml` fails on `main` since run 40752724206 (2026-10-28) and on every PR after it, such as #64. It fails at `actions/setup-python@v5` before any test runs:

    The version '3.9' with architecture 'x64' was not found for Ubuntu 26.04.

`ubuntu-latest` moved to Ubuntu 26.04, and the Python builds for that image start at 3.10. `pyproject.toml` still says `requires-python = ">=3.9"`.

Two ways to fix it, and the choice is the maintainer's:

- Drop 3.9 from the matrix and raise `requires-python` to `>=3.10`. Python 3.9 reached end of life in October 2025.
- Keep 3.9 support and pin that matrix entry to `runs-on: ubuntu-24.04`.
