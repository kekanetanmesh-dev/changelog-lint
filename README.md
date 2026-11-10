# changelog-lint

**A changelog that lies is worse than none.** `changelog-lint` checks `CHANGELOG.md` against the [Keep a Changelog](https://keepachangelog.com/) format so that release order, dates, section names and the `Unreleased` block stay right, in CI and before commit.

```
$ changelog-lint
CHANGELOG.md:5: error: missing '## [Unreleased]' section [CL020]
CHANGELOG.md:14: error: version 1.2.0 should come after 1.3.0 (newest first) [CL032]
CHANGELOG.md:16: error: unknown change type 'Fixes'; did you mean 'Fixed'? [CL050]
CHANGELOG.md:22: error: date 2026-13-01 is not a real date [CL041]
4 error(s), 0 warning(s)
```

Zero dependencies, Python 3.9+, runs as a CLI, a pre-commit hook, or a GitHub Action.

## Install

```bash
pip install changelog-lint
changelog-lint                    # lints ./CHANGELOG.md
changelog-lint docs/HISTORY.md    # or any file(s)
```

### pre-commit

```yaml
repos:
  - repo: https://github.com/kekanetanmesh-dev/changelog-lint
    rev: v0.1.0
    hooks:
      - id: changelog-lint
```

### GitHub Action

```yaml
- uses: kekanetanmesh-dev/changelog-lint@v0.1.0
  with:
    args: --require-links
```

Problems show up as inline annotations on the pull request.

## Rules

| Code | Checks |
|---|---|
| CL000, CL001, CL002 | One `# Changelog` top-level heading |
| CL010, CL011 | Every `##` heading is `[version] - date`, `[Unreleased]`, or `[version] - date [YANKED]`; `###` headings live under a release |
| CL020–CL023 | `[Unreleased]` exists, is first, is unique, has no date |
| CL030–CL033 | Versions are unique, valid semver (`v` prefix allowed), newest first; pre-releases sort before their release |
| CL040–CL043 | Every release has an ISO date that is real, not in the future, and not later than a newer release (warning) |
| CL050, CL051 | Change types are `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, each at most once per release |
| CL060, CL061 | Releases have entries (yanked ones may be empty) |
| CL070 | With `--require-links`: every release has a `[x.y.z]: url` reference |

Fenced code blocks are skipped, so example headings inside them do not trip the linter.

## Options

```
--no-unreleased        don't require an [Unreleased] section
--require-links        require a link reference for every release
--allow-future-dates   useful for release branches cut ahead of time
--loose-semver         accept CalVer or other schemes (ordering checks are skipped for them)
--format text|json|github
-W, --warnings-as-errors
```

Exit code `0` clean, `1` problems, `2` file not found.

## Library

```python
from changelog_lint import lint_text
from changelog_lint.linter import Options

for p in lint_text(open("CHANGELOG.md").read(), Options(require_links=True)):
    print(p.line, p.code, p.message)
```

## Contributing

```bash
pip install -e .
python -m unittest discover -s tests -v
```

Ideas welcome: a `--fix` that reorders sections, CalVer ordering, a check that `[Unreleased]` is empty on a release commit, and a rule that every entry mentions a PR or issue. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
