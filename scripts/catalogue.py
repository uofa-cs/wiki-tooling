"""Sync course facts from the UAlberta catalogue (apps.ualberta.ca/catalogue).

Usage:
    python scripts/catalogue.py fetch [--out catalogue.json]
        Fetch every undergraduate CMPUT course and write the facts as JSON.

    python scripts/catalogue.py nav wiki-content/docs/courses
        Print the Courses section of nav.yml, grouped by level, or rewrite it
        in place with --update wiki-content/nav.yml.

    python scripts/catalogue.py check wiki-content/docs/courses
        Compare each course page's frontmatter with the catalogue and report
        drift (title, units, prerequisites, terms). Exits 1 if anything drifted.

    python scripts/catalogue.py seed wiki-content/docs/courses [--since 1890]
        Create a page for every course offered in or after the given term code
        (1890 = Fall 2024) that doesn't have one yet, and refresh the catalogue
        fields in existing pages' frontmatter. Body text is never touched.

Only the catalogue owns these fields: code, title, units, description,
prerequisites, corequisites, exclusions, terms, latest_term, catalogue.
Everything else on a page belongs to contributors.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import yaml

BASE = "https://apps.ualberta.ca/catalogue/course/cmput"
CATALOGUE_FIELDS = (
    "code", "title", "units", "description", "prerequisites",
    "corequisites", "exclusions", "terms", "latest_term", "catalogue",
)
# Directed study, co-op, and special-topics shells aren't real courses to review.
SKIP = {"296", "297", "298", "299", "396", "397", "398", "496", "497", "498"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "uofa-cs-wiki-catalogue-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def undergrad_codes() -> list[str]:
    codes = set(re.findall(r"/catalogue/course/cmput/(\d{3})\b", get(BASE)))
    return sorted(c for c in codes if int(c) < 500 and c not in SKIP)


def term_label(name: str) -> str:
    """'Winter Term 2026' -> 'W26'."""
    season, _, year = name.split()
    return {"Fall": "F", "Winter": "W", "Spring": "Sp", "Summer": "Su"}[season] + year[2:]


def split_requirements(desc: str) -> tuple[str, str, str, str]:
    """Pull prerequisite/corequisite/credit-exclusion sentences out of a description."""
    sentences = re.split(r"(?<=\.)\s+(?=[A-Z])", desc)
    keep, pre, co, excl = [], [], [], []
    for s in sentences:
        low = s.lower()
        if low.startswith(("prerequisite", "prerequisites")):
            pre.append(re.sub(r"^Prerequisites?:\s*", "", s))
        elif low.startswith(("corequisite", "corequisites")):
            co.append(re.sub(r"^Corequisites?:\s*", "", s))
        elif low.startswith("credit cannot be obtained") or low.startswith("not open to students with credit"):
            excl.append(s)
        else:
            keep.append(s)
    return " ".join(keep), " ".join(pre), " ".join(co), " ".join(excl)


def fetch_course(code: str) -> dict:
    page = get(f"{BASE}/{code}")
    title = text(re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S).group(1))
    title = re.sub(r"^CMPUT\s+\w+\s+-\s+", "", title)
    units_m = re.search(r"<h2[^>]*>\s*([\d.]+) units", page)
    desc_m = re.search(r"Faculty of Science</a></p>\s*<p>(.*?)</p>", page, re.S)
    desc = text(desc_m.group(1)) if desc_m else ""
    summary, pre, co, excl = split_requirements(desc)
    terms = []
    for href, name in re.findall(r'class="dropdown-item[^"]*"\s+href="([^"]+)">([^<]+)</a>', page):
        tid = re.search(r"(\d{4})$", href) or re.search(r"#(\d{4})$", href)
        if tid:
            terms.append((int(tid.group(1)), term_label(name.strip())))
    terms.sort(reverse=True)
    return {
        "code": f"CMPUT {code}",
        "title": title,
        "units": float(units_m.group(1)) if units_m else None,
        "description": summary,
        "prerequisites": pre,
        "corequisites": co,
        "exclusions": excl,
        "terms": [label for _, label in terms],
        "term_codes": [tid for tid, _ in terms],
        "latest_term": terms[0][1] if terms else "",
        "catalogue": f"{BASE}/{code}",
    }


def fetch_all() -> list[dict]:
    codes = undergrad_codes()
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        return list(pool.map(fetch_course, codes))


FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def read_page(path: Path) -> tuple[dict, str]:
    raw = path.read_text()
    m = FRONTMATTER.match(raw)
    if not m:
        return {}, raw
    return yaml.safe_load(m.group(1)) or {}, raw[m.end():]


def write_page(path: Path, meta: dict, body: str) -> None:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text(f"---\n{fm}---\n{body}")


def page_path(courses_dir: Path, code: str) -> Path:
    return courses_dir / f"cmput-{code.split()[1]}.md"


def catalogue_meta(c: dict) -> dict:
    meta = {k: c[k] for k in CATALOGUE_FIELDS}
    meta["terms"] = c["terms"][:8]  # recent history is enough
    return meta


def stub_body(c: dict) -> str:
    return f"""
# {c['code']}: {c['title']}

## What Students Say

Nobody has reviewed this course yet. If you've taken it, [add a review](https://github.com/uofa-cs/uofa-cs-wiki/issues/new?template=course-review.yml) (no git needed).
"""


def cmd_fetch(args) -> None:
    data = fetch_all()
    Path(args.out).write_text(json.dumps(data, indent=2))
    print(f"wrote {len(data)} courses to {args.out}")


def cmd_seed(args) -> None:
    courses_dir = Path(args.dir)
    data = fetch_all()
    created = updated = 0
    for c in data:
        path = page_path(courses_dir, c["code"])
        recent = any(t >= args.since for t in c["term_codes"])
        if path.exists():
            meta, body = read_page(path)
            new = {**meta, **catalogue_meta(c)}
            if new != meta:
                new["last_verified"] = date.today().isoformat()
                write_page(path, new, body)
                updated += 1
        elif recent:
            meta = {**catalogue_meta(c), "difficulty": None, "workload": None,
                    "last_verified": date.today().isoformat()}
            write_page(path, meta, stub_body(c))
            created += 1
    print(f"created {created}, updated {updated}")


def cmd_check(args) -> None:
    courses_dir = Path(args.dir)
    by_code = {c["code"]: c for c in fetch_all()}
    drift = 0
    for path in sorted(courses_dir.glob("cmput-*.md")):
        meta, _ = read_page(path)
        c = by_code.get(meta.get("code"))
        if not c:
            print(f"{path.name}: not in the catalogue any more")
            drift += 1
            continue
        for k, v in catalogue_meta(c).items():
            if meta.get(k) != v:
                print(f"{path.name}: {k} changed\n  page:      {meta.get(k)!r}\n  catalogue: {v!r}")
                drift += 1
    print(f"{drift} difference(s)")
    sys.exit(1 if drift else 0)


def cmd_nav(args) -> None:
    courses_dir = Path(args.dir)
    groups: dict[str, list[str]] = {}
    for path in sorted(courses_dir.glob("cmput-*.md")):
        meta, _ = read_page(path)
        level = meta["code"].split()[1][0] + "00-level"
        groups.setdefault(level, []).append(
            f"      - \"{meta['code']}: {meta['title']}\": docs/courses/{path.name}")
    lines = ["  - Courses:", "    - All Courses: docs/courses/index.md"]
    for level, items in groups.items():
        lines.append(f"    - {level}:")
        lines.extend(items)
    block = "\n".join(lines) + "\n"
    if not args.update:
        print(block, end="")
        return
    nav = Path(args.update)
    text, n = re.subn(r"  - Courses:\n(?:    .*\n)+", lambda _: block, nav.read_text())
    if n != 1:
        sys.exit(f"couldn't find the Courses section in {nav}")
    nav.write_text(text)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    f = sub.add_parser("fetch"); f.add_argument("--out", default="catalogue.json"); f.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("seed"); s.add_argument("dir"); s.add_argument("--since", type=int, default=1890); s.set_defaults(fn=cmd_seed)
    n = sub.add_parser("nav"); n.add_argument("dir"); n.add_argument("--update", metavar="NAV_YML"); n.set_defaults(fn=cmd_nav)
    c = sub.add_parser("check"); c.add_argument("dir"); c.set_defaults(fn=cmd_check)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
