"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from . import __version__
from .linter import Options, lint


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="changelog-lint",
        description="Lint CHANGELOG.md against the Keep a Changelog format.",
    )
    p.add_argument("files", nargs="*", default=["CHANGELOG.md"], help="changelog files (default: CHANGELOG.md)")
    p.add_argument("--no-unreleased", action="store_true", help="do not require an [Unreleased] section")
    p.add_argument("--require-links", action="store_true", help="require a link reference for every release")
    p.add_argument("--allow-future-dates", action="store_true", help="do not flag release dates after today")
    p.add_argument("--loose-semver", action="store_true", help="accept versions that are not semver")
    p.add_argument("--format", choices=["text", "json", "github"], default="text")
    p.add_argument("--warnings-as-errors", "-W", action="store_true")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    opts = Options(
        require_unreleased=not args.no_unreleased,
        require_links=args.require_links,
        allow_future_dates=args.allow_future_dates,
        strict_semver=not args.loose_semver,
    )
    all_problems = []
    for path in args.files:
        try:
            problems = lint(path, opts)
        except FileNotFoundError:
            print(f"{path}: error: file not found", file=sys.stderr)
            return 2
        for pr in problems:
            all_problems.append((path, pr))

    if args.format == "json":
        print(json.dumps([
            {"file": f, "line": p.line, "code": p.code, "severity": p.severity, "message": p.message}
            for f, p in all_problems
        ], indent=2))
    elif args.format == "github":
        for f, p in all_problems:
            print(f"::{p.severity} file={f},line={p.line},title={p.code}::{p.message}")
    else:
        for f, p in all_problems:
            print(f"{f}:{p.line}: {p.severity}: {p.message} [{p.code}]")
        errors = sum(1 for _, p in all_problems if p.severity == "error")
        warnings = len(all_problems) - errors
        if not all_problems:
            print(f"ok: {', '.join(args.files)}")
        else:
            print(f"{errors} error(s), {warnings} warning(s)")

    failing = [p for _, p in all_problems if p.severity == "error" or args.warnings_as_errors]
    return 1 if failing else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
