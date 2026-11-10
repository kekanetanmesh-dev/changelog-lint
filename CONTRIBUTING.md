# Contributing

## Setup

```bash
git clone https://github.com/kekanetanmesh-dev/changelog-lint
cd changelog-lint
pip install -e .
python -m unittest discover -s tests -v
```

No dependencies beyond the standard library; keep it that way.

## Adding a rule

1. Pick the next free code in the right block (`CL0xx` by topic; see README).
2. Implement it in `src/changelog_lint/linter.py` as a pure check over the parsed structure.
3. Add a test in `tests/test_linter.py` that triggers it and one that shows a clean file still passes.
4. Add the row to the README table and a line under `[Unreleased]` in `CHANGELOG.md`.

## Good first issues

- `--fix` to sort change-type sections into the canonical order.
- CalVer-aware ordering under `--loose-semver`.
- A rule that flags entries without a PR/issue reference (opt-in).
