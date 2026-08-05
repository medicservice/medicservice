#!/usr/bin/env python3
"""Rimuove lo snippet Iubenda dall'head (banner gestito via GTM template)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- Iubenda Cookie Solution -->"
SKIP = set()


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER not in text:
        return False

    updated = re.sub(
        r"\n<!-- Iubenda Cookie Solution -->.*?"
        r'<script type="text/javascript" src="//cdn\.iubenda\.com/cs/iubenda_cs\.js" charset="UTF-8" async></script>\n',
        "\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if updated == text:
        return False

    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    updated = []
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in SKIP or "_ds/" in rel:
            continue
        if patch(path):
            updated.append(path.relative_to(ROOT))
    print(f"Updated {len(updated)} file(s)")
    for p in updated:
        print(f"  {p}")


if __name__ == "__main__":
    main()
