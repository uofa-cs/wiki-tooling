"""Render course facts from page frontmatter.

Course pages (docs/courses/cmput-NNN.md) keep catalogue facts in frontmatter,
synced by scripts/catalogue.py. This hook:

- inserts an "At a glance" box under each course page's title, and
- replaces <!-- course-index --> on any page with a table of all courses.

Contributors only edit the page body; the facts stay machine-checkable.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

COURSE_PAGE = re.compile(r"^docs/courses/cmput-(\d{3})\.md$")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SEASON_MONTH = {"W": 1, "Sp": 5, "Su": 7, "F": 9}
STALE_YEARS = 2


def term_start(label: str) -> date:
    m = re.match(r"(W|Sp|Su|F)(\d\d)$", label)
    return date(2000 + int(m.group(2)), SEASON_MONTH[m.group(1)], 1)


def term_end(label: str) -> date:
    start = term_start(label)
    month = start.month + 4
    return date(start.year + (month > 12), (month - 1) % 12 + 1, 1)


def term_name(label: str) -> str:
    m = re.match(r"(W|Sp|Su|F)(\d\d)$", label)
    season = {"W": "Winter", "Sp": "Spring", "Su": "Summer", "F": "Fall"}[m.group(1)]
    return f"{season} 20{m.group(2)}"


def offering_summary(terms: list[str]) -> tuple[str, bool]:
    """Return (text, is_stale). A term counts as current for its first four months."""
    if not terms:
        return "No offerings listed in the catalogue", True
    today = date.today()
    current = [t for t in terms if term_start(t) <= today < term_end(t)]
    upcoming = [t for t in terms if term_start(t) > today]
    past = [t for t in terms if term_end(t) <= today]
    parts = []
    if current:
        parts.append("Now: " + term_name(current[0]))
    if upcoming:
        parts.append("Scheduled: " + ", ".join(term_name(t) for t in sorted(upcoming, key=term_start)))
    if past and not (current or upcoming):
        parts.append("Last offered: " + term_name(past[0]))
    stale = not (current or upcoming) and (not past or (today - term_start(past[0])).days > 365 * STALE_YEARS)
    return "; ".join(parts), stale


def facts_box(meta: dict) -> str:
    offered, stale = offering_summary(meta.get("terms") or [])
    rows = [("Units", f"{meta['units']:g}" if meta.get("units") is not None else "")]
    for key, label in (("prerequisites", "Prerequisites"), ("corequisites", "Corequisites"),
                       ("exclusions", "Credit exclusions")):
        if meta.get(key):
            rows.append((label, meta[key]))
    rows.append(("Offered", offered))
    for key, label in (("difficulty", "Difficulty"), ("workload", "Workload"),
                       ("languages", "Languages and tools"), ("textbook", "Textbook")):
        value = meta.get(key)
        if value:
            rows.append((label, ", ".join(value) if isinstance(value, list) else str(value)))
    lines = []
    if stale:
        lines += ['!!! warning "Not recently offered"',
                  "    This course hasn't run in the last two years and isn't scheduled. Don't plan around it.", ""]
    lines += ['!!! info "At a glance"', ""]
    lines += [f"    - **{k}:** {v}" for k, v in rows if v]
    if meta.get("description"):
        lines += ["", f"    {meta['description']}"]
    links = [f"[Official catalogue entry]({meta['catalogue']})"]
    if meta.get("course_site"):
        links.append(f"[Course website]({meta['course_site']})")
    lines += ["", "    " + " · ".join(links) + f" · facts synced {meta.get('last_verified', 'unknown')}", ""]
    return "\n".join(lines)


def read_meta(path: Path) -> dict:
    m = FRONTMATTER.match(path.read_text())
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def compact_offering(terms: list[str]) -> str:
    today = date.today()
    soon = [t for t in terms if term_end(t) > today]
    if soon:
        return ", ".join(sorted(soon, key=term_start))
    if not terms or (today - term_start(terms[0])).days > 365 * STALE_YEARS:
        return "Not recently offered"
    return f"Last: {terms[0]}"


def has_reviews(path: Path) -> bool:
    return "Nobody has reviewed this course yet" not in path.read_text()


def course_index(docs_dir: Path, from_page: str) -> str:
    rows = []
    for path in sorted((docs_dir / "docs/courses").glob("cmput-*.md")):
        meta = read_meta(path)
        rel = Path("../" * from_page.count("/")) / path.relative_to(docs_dir)
        number = meta["code"].split()[1]
        rows.append((number[0] + "00", f"| [CMPUT&nbsp;{number}]({rel.as_posix()}) | {meta.get('title', '')} | "
                                      f"{meta.get('difficulty') or ''} | {meta.get('workload') or ''} | "
                                      f"{compact_offering(meta.get('terms') or [])} | "
                                      f"{'Yes' if has_reviews(path) else ''} |"))
    out = []
    for level in sorted({r[0] for r in rows}):
        out += [f"### {level}-level", "",
                "| Course | Title | Difficulty | Workload | Offered | Reviews |",
                "|---|---|---|---|---|---|"]
        out += [r[1] for r in rows if r[0] == level]
        out.append("")
    return "\n".join(out)


def on_page_markdown(markdown, page, config, files, **kwargs):
    src = page.file.src_uri
    if COURSE_PAGE.match(src) and page.meta.get("code"):
        page.meta["title"] = f"{page.meta['code']}: {page.meta['title']}"
        lines = markdown.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("# "):
                lines[i + 1:i + 1] = ["", facts_box(page.meta)]
                break
        markdown = "\n".join(lines)
    if "<!-- course-index -->" in markdown:
        markdown = markdown.replace("<!-- course-index -->", course_index(Path(config["docs_dir"]), src))
    return markdown
