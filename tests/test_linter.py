import unittest
from datetime import date

from changelog_lint import lint_text
from changelog_lint.linter import Options, parse_semver

TODAY = date(2026, 11, 10)
OPTS = Options(today=TODAY)

GOOD = """# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Something coming.

## [1.1.0] - 2026-10-01

### Added

- New flag.

### Fixed

- Bug.

## [1.0.0] - 2026-01-15

### Added

- First release.

[Unreleased]: https://example.com/compare/v1.1.0...HEAD
[1.1.0]: https://example.com/compare/v1.0.0...v1.1.0
[1.0.0]: https://example.com/releases/tag/v1.0.0
"""


def codes(text, opts=OPTS):
    return [p.code for p in lint_text(text, opts)]


class LinterTests(unittest.TestCase):
    def test_good_file_is_clean(self):
        self.assertEqual(codes(GOOD), [])
        self.assertEqual(codes(GOOD, Options(today=TODAY, require_links=True)), [])

    def test_missing_h1_and_unreleased(self):
        self.assertIn("CL000", codes("## [1.0.0] - 2026-01-01\n- x\n"))
        self.assertIn("CL020", codes("# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n"))
        self.assertNotIn("CL020", codes("# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n", Options(today=TODAY, require_unreleased=False)))

    def test_version_order_and_duplicates(self):
        text = "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n- a\n\n## [1.1.0] - 2026-02-01\n- b\n\n## [1.1.0] - 2026-02-01\n- c\n"
        c = codes(text)
        self.assertIn("CL032", c)
        self.assertIn("CL030", c)

    def test_prerelease_sorts_before_release(self):
        self.assertLess(parse_semver("1.0.0-rc.1"), parse_semver("1.0.0"))
        self.assertLess(parse_semver("1.0.0-alpha"), parse_semver("1.0.0-beta"))
        self.assertLess(parse_semver("1.0.0-rc.1"), parse_semver("1.0.0-rc.2"))
        text = "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-02-01\n- a\n\n## [1.0.0-rc.1] - 2026-01-01\n- b\n"
        self.assertEqual(codes(text), [])

    def test_dates(self):
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0]\n- a\n")
        self.assertIn("CL040", c)
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 01/02/2026\n- a\n")
        self.assertIn("CL041", c)
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-02-30\n- a\n")
        self.assertIn("CL041", c)
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2030-01-01\n- a\n")
        self.assertIn("CL042", c)
        self.assertNotIn("CL042", codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2030-01-01\n- a\n", Options(today=TODAY, allow_future_dates=True)))
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.1.0] - 2026-01-01\n- a\n\n## [1.0.0] - 2026-02-01\n- b\n")
        self.assertIn("CL043", c)

    def test_unreleased_rules(self):
        c = codes("# Changelog\n\n## [1.0.0] - 2026-01-01\n- a\n\n## [Unreleased] - 2026-01-02\n")
        self.assertIn("CL022", c)
        self.assertIn("CL023", c)

    def test_change_types(self):
        text = "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n\n### Fixes\n- a\n\n### Added\n- b\n\n### Added\n- c\n"
        probs = lint_text(text, OPTS)
        msgs = {p.code: p.message for p in probs}
        self.assertIn("CL050", msgs)
        self.assertIn("did you mean 'Fixed'", msgs["CL050"])
        self.assertIn("CL051", msgs)

    def test_empty_release(self):
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n\n## [0.9.0] - 2025-12-01\n- ok\n")
        self.assertIn("CL060", c)
        # yanked releases may be empty
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01 [YANKED]\n\n## [0.9.0] - 2025-12-01\n- ok\n")
        self.assertNotIn("CL060", c)

    def test_semver(self):
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0] - 2026-01-01\n- a\n")
        self.assertIn("CL031", c)
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0] - 2026-01-01\n- a\n", Options(today=TODAY, strict_semver=False))
        self.assertNotIn("CL031", c)
        self.assertEqual(codes("# Changelog\n\n## [Unreleased]\n\n## [v1.0.0] - 2026-01-01\n- a\n"), [])

    def test_links_required(self):
        c = codes("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n- a\n", Options(today=TODAY, require_links=True))
        self.assertEqual(c.count("CL070"), 2)

    def test_code_blocks_are_ignored(self):
        text = GOOD + "\n```\n## [9.9.9]\n### Nope\n```\n"
        self.assertEqual(codes(text), [])

    def test_heading_not_understood(self):
        c = codes("# Changelog\n\n## [Unreleased]\n\n## Release notes for 1.0\n- a\n")
        self.assertIn("CL010", c)


if __name__ == "__main__":
    unittest.main()
