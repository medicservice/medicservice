#!/usr/bin/env python3
"""Collega mobilebar e drawer delle schede medico a MioDottore (idempotente)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIODOTTOR = "https://www.miodottore.it/strutture/medic-service-oristano"
MARKER = f'href="{MIODOTTOR}" target="_blank" rel="noopener"><i data-lucide="calendar-check"></i> Prenota</a>'

MOBILEBAR_OLD = re.compile(
    r'<a class="mobilebar__book" data-book(?: data-medico="[^"]*")?>'
    r'<i data-lucide="calendar-check"></i> Prenota</a>'
)
MOBILEBAR_NEW = (
    f'<a class="mobilebar__book" href="{MIODOTTOR}" target="_blank" rel="noopener">'
    f'<i data-lucide="calendar-check"></i> Prenota</a>'
)

DRAWER_OLD = re.compile(
    r'<button class="btn btn--primary btn--block" data-book(?: data-medico="[^"]*")? '
    r'style="margin-top:20px" data-close-drawer>Prenota online</button>'
)
DRAWER_NEW = (
    f'<a class="btn btn--primary btn--block" href="{MIODOTTOR}" target="_blank" rel="noopener" '
    f'style="margin-top:20px" data-close-drawer>Prenota online</a>'
)

MODAL_BLOCK = re.compile(
    r"\n<!-- ===== BOOKING MODAL ===== -->.*?"
    r"</div>\n\n+(?=<script type=\"text/javascript\">\(function \(w,d\))",
    re.DOTALL,
)


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    if MOBILEBAR_OLD.search(text):
        text = MOBILEBAR_OLD.sub(MOBILEBAR_NEW, text, count=1)

    if DRAWER_OLD.search(text):
        text = DRAWER_OLD.sub(DRAWER_NEW, text, count=1)

    text = MODAL_BLOCK.sub("\n\n", text)

    if text == original:
        return False

    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    updated = []
    for path in sorted((ROOT / "medici").glob("*/index.html")):
        if patch(path):
            updated.append(path.relative_to(ROOT))
    print(f"Updated {len(updated)} file(s)")
    for p in updated:
        print(f"  {p}")


if __name__ == "__main__":
    main()
