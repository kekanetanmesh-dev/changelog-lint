import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from changelog_lint.cli import main


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_clean_file_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2020-01-01\n- a\n")
            code, out = self.run_cli([p])
            self.assertEqual(code, 0)
            self.assertIn("ok:", out)

    def test_errors_exit_one_and_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "CHANGELOG.md", "# Changelog\n\n## [1.0.0]\n- a\n")
            code, out = self.run_cli([p])
            self.assertEqual(code, 1)
            self.assertIn("CL040", out)
            code, out = self.run_cli([p, "--format", "json"])
            data = json.loads(out)
            self.assertTrue(any(d["code"] == "CL020" for d in data))
            code, out = self.run_cli([p, "--format", "github"])
            self.assertIn("::error file=", out)

    def test_warnings_as_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "CHANGELOG.md", "# History\n\n## [Unreleased]\n\n## [1.0.0] - 2020-01-01\n- a\n")
            self.assertEqual(self.run_cli([p])[0], 0)
            self.assertEqual(self.run_cli([p, "-W"])[0], 1)

    def test_missing_file(self):
        self.assertEqual(main(["/nonexistent/CHANGELOG.md"]), 2)


if __name__ == "__main__":
    unittest.main()
