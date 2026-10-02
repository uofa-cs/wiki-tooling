"""List wiki pages whose "Last verified" date is older than a threshold.

Usage:
    python scripts/staleness.py wiki-content [--months 12]

Looks for "Last verified: October 2026" lines in page bodies. Prints a
Markdown checklist of stale pages (for an issue body) and exits 1 if any are
stale, 0 otherwise. Course pages are skipped: their facts are synced from the
catalogue by scripts/catalogue.py.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October November December".split(), 1)}
VERIFIED = re.compile(r"Last verified:?\**\s*(" + "|".join(MONTHS) + r")\s+(\d{4})", re.I)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("--months", type=int, default=12)
    args = p.parse_args()

    root = Path(args.root)
    today = date.today()
    stale, unverified = [], []
    for path in sorted(root.glob("docs/**/*.md")):
        rel = path.relative_to(root).as_posix()
        if re.match(r"docs/courses/cmput-\d{3}\.md$", rel):
            continue
        m = VERIFIED.search(path.read_text())
        if not m:
            unverified.append(rel)
            continue
        month, year = MONTHS[m.group(1).capitalize()], int(m.group(2))
        age = (today.year - year) * 12 + today.month - month
        if age > args.months:
            stale.append((rel, f"{m.group(1).capitalize()} {year}"))

    if stale:
        print(f"These pages were last verified more than {args.months} months ago. "
              "Re-check their facts against the linked sources, then update the date.\n")
        for rel, when in stale:
            print(f"- [ ] `{rel}` (last verified {when})")
    if unverified:
        print("\nThese pages have no \"Last verified\" line:\n")
        for rel in unverified:
            print(f"- `{rel}`")
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
