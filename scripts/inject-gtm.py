#!/usr/bin/env python3
"""Inietta Google Tag Manager in tutte le pagine HTML del sito (idempotente)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GTM_ID = "GTM-TKGKM6ZJ"
MARKER = GTM_ID

GTM_HEAD = """
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-TKGKM6ZJ');</script>
<!-- End Google Tag Manager -->
"""

GTM_BODY = """
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-TKGKM6ZJ"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
"""

SKIP = set()


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False

    changed = False

    if "<head>" in text:
        text = text.replace("<head>", "<head>" + GTM_HEAD, 1)
        changed = True

    body_match = re.search(r"<body[^>]*>", text)
    if body_match:
        insert_at = body_match.end()
        text = text[:insert_at] + GTM_BODY + text[insert_at:]
        changed = True

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


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
