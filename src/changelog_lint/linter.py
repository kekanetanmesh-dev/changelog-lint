"""Core linter. Pure functions over text, no I/O, so it is easy to test."""

from __future__ import annotations

import re
from difflib import get_close_matches
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List, Optional, Tuple

CHANGE_TYPES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")

H1_RE = re.compile(r"^#\s+(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
# ## [1.2.3] - 2024-01-31   |  ## [Unreleased]  |  ## 1.2.3 (2024-01-31)  | ## [1.2.3] - 2024-01-31 [YANKED]
VERSION_HEADING_RE = re.compile(
    r"^\[?(?P<version>Unreleased|[^\]\s]+)\]?"
    r"(?:\s*[-–—]\s*(?P<date>\S+))?"
    r"(?:\s*\[(?P<flag>[A-Z]+)\])?\s*$",
    re.IGNORECASE,
)
SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)
LINK_REF_RE = re.compile(r"^\[([^\]]+)\]:\s*(\S+)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Problem:
    line: int
    code: str
    message: str
    severity: str = "error"  # or "warning"

    def __str__(self) -> str:
        return f"{self.line}: {self.severity}: {self.code} {self.message}"


@dataclass
class Release:
    version: str
    line: int
    date: Optional[str] = None
    flag: Optional[str] = None
    sections: List[Tuple[str, int]] = field(default_factory=list)
    body_lines: int = 0  # non-blank lines under the release, excluding headings


@dataclass
class Options:
    require_unreleased: bool = True
    require_links: bool = False
    allow_future_dates: bool = False
    strict_semver: bool = True
    today: Optional[date] = None


def parse_semver(v: str) -> Optional[Tuple[int, int, int, Tuple]]:
    m = SEMVER_RE.match(v)
    if not m:
        return None
    pre = m.group("pre")
    # A pre-release sorts before the release: (1,) > (0, ...)
    pre_key: Tuple = (1,) if pre is None else (0,) + tuple(
        (0, int(p)) if p.isdigit() else (1, p) for p in pre.split(".")
    )
    return (int(m.group("major")), int(m.group("minor")), int(m.group("patch")), pre_key)


def _parse(text: str) -> Tuple[Optional[Tuple[str, int]], List[Release], dict, List[Problem]]:
    problems: List[Problem] = []
    h1: Optional[Tuple[str, int]] = None
    releases: List[Release] = []
    links: dict = {}
    in_code = False
    current: Optional[Release] = None

    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\n")
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if (m := H1_RE.match(line)):
            if h1 is None:
                h1 = (m.group(1), i)
            else:
                problems.append(Problem(i, "CL001", "more than one top-level heading"))
            continue
        if (m := H2_RE.match(line)):
            vm = VERSION_HEADING_RE.match(m.group(1).strip())
            if not vm:
                problems.append(Problem(i, "CL010", f"release heading not understood: {m.group(1)!r}"))
                current = None
                continue
            current = Release(
                version=vm.group("version"),
                line=i,
                date=vm.group("date"),
                flag=(vm.group("flag") or None),
            )
            releases.append(current)
            continue
        if (m := H3_RE.match(line)):
            if current is not None:
                current.sections.append((m.group(1).strip(), i))
            else:
                problems.append(Problem(i, "CL011", "change-type heading outside of any release"))
            continue
        if (m := LINK_REF_RE.match(line)):
            links[m.group(1)] = m.group(2)
            continue
        if current is not None and line.strip():
            current.body_lines += 1
    return h1, releases, links, problems


def lint_text(text: str, options: Optional[Options] = None) -> List[Problem]:
    opts = options or Options()
    today = opts.today or date.today()
    h1, releases, links, problems = _parse(text)

    if h1 is None:
        problems.append(Problem(1, "CL000", "missing top-level '# Changelog' heading"))
    elif h1[0].strip().lower() not in ("changelog", "change log"):
        problems.append(Problem(h1[1], "CL002", f"top-level heading should be 'Changelog', got {h1[0]!r}", "warning"))

    unreleased = [r for r in releases if r.version.lower() == "unreleased"]
    versioned = [r for r in releases if r.version.lower() != "unreleased"]

    if opts.require_unreleased and not unreleased:
        problems.append(Problem(h1[1] if h1 else 1, "CL020", "missing '## [Unreleased]' section"))
    if len(unreleased) > 1:
        problems.append(Problem(unreleased[1].line, "CL021", "more than one Unreleased section"))
    if unreleased and releases and releases[0] is not unreleased[0]:
        problems.append(Problem(unreleased[0].line, "CL022", "Unreleased should be the first release section"))
    for r in unreleased:
        if r.date:
            problems.append(Problem(r.line, "CL023", "Unreleased must not have a date"))

    seen = set()
    prev: Optional[Release] = None
    for r in versioned:
        key = r.version.lower().lstrip("v")
        if key in seen:
            problems.append(Problem(r.line, "CL030", f"duplicate version {r.version}"))
        seen.add(key)

        sv = parse_semver(r.version)
        if opts.strict_semver and sv is None:
            problems.append(Problem(r.line, "CL031", f"version {r.version!r} is not valid semver"))

        valid_date = False
        if not r.date:
            problems.append(Problem(r.line, "CL040", f"release {r.version} has no date"))
        elif not DATE_RE.match(r.date):
            problems.append(Problem(r.line, "CL041", f"date {r.date!r} is not ISO 8601 (YYYY-MM-DD)"))
        else:
            try:
                d = date.fromisoformat(r.date)
                valid_date = True
                if d > today and not opts.allow_future_dates:
                    problems.append(Problem(r.line, "CL042", f"date {r.date} is in the future"))
            except ValueError:
                problems.append(Problem(r.line, "CL041", f"date {r.date!r} is not a real date"))
        if not valid_date:
            r.date = None

        if prev is not None:
            psv = parse_semver(prev.version)
            if sv and psv and sv >= psv:
                problems.append(Problem(r.line, "CL032", f"version {r.version} should come after {prev.version} (newest first)"))
            if prev.date and r.date and r.date > prev.date:
                problems.append(Problem(r.line, "CL043", f"date {r.date} is later than the newer release {prev.version} ({prev.date})", "warning"))
        prev = r

        if r.flag and r.flag.upper() != "YANKED":
            problems.append(Problem(r.line, "CL033", f"unknown release flag [{r.flag}]", "warning"))

    for r in releases:
        names = []
        for name, line in r.sections:
            if name not in CHANGE_TYPES:
                close = get_close_matches(name.capitalize(), CHANGE_TYPES, n=1, cutoff=0.6)
                hint = close[0] if close else None
                msg = f"unknown change type '{name}'" + (f"; did you mean '{hint}'?" if hint else f"; use one of {', '.join(CHANGE_TYPES)}")
                problems.append(Problem(line, "CL050", msg))
            if name in names:
                problems.append(Problem(line, "CL051", f"'{name}' appears twice in {r.version}"))
            names.append(name)
        if r.version.lower() != "unreleased" and r.body_lines == 0 and not r.flag:
            problems.append(Problem(r.line, "CL060", f"release {r.version} has no entries"))
        if r.sections and r.body_lines == 0 and r.version.lower() == "unreleased":
            problems.append(Problem(r.line, "CL061", "Unreleased has change-type headings but no entries", "warning"))

    if opts.require_links:
        for r in releases:
            if r.version not in links and r.version.lower() != "unreleased" or (r.version.lower() == "unreleased" and "Unreleased" not in links):
                problems.append(Problem(r.line, "CL070", f"no link reference for [{r.version}]"))

    problems.sort(key=lambda p: (p.line, p.code))
    return problems


def lint(path: str, options: Optional[Options] = None) -> List[Problem]:
    with open(path, encoding="utf-8") as fh:
        return lint_text(fh.read(), options)


def iter_errors(problems: Iterable[Problem]) -> Iterable[Problem]:
    return (p for p in problems if p.severity == "error")
