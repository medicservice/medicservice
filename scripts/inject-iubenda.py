#!/usr/bin/env python3
"""Inietta snippet Iubenda in tutte le pagine HTML del sito (idempotente)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

IUBENDA_HEAD = """
<!-- Iubenda Cookie Solution -->
<script type="text/javascript">
var _iub = _iub || [];
_iub.csConfiguration = {"askConsentAtCookiePolicyUpdate":true,"countryDetection":true,"emailMarketing":{"theme":"dark"},"enableFadp":true,"enableLgpd":true,"enableUspr":true,"lgpdAppliesGlobally":false,"perPurposeConsent":true,"siteId":305777,"whitelabel":false,"cookiePolicyId":865793,"banner":{"acceptButtonDisplay":true,"closeButtonRejects":true,"customizeButtonDisplay":true,"explicitWithdrawal":true,"fontSizeBody":"12px","listPurposes":true,"logo":null,"ownerName":"medicservice.it","position":"float-bottom-right","rejectButtonDisplay":true,"showPurposesToggles":true,"showTotalNumberOfProviders":true}};
_iub.csLangConfiguration = {"it":{"cookiePolicyId":865793}};
</script>
<script type="text/javascript" src="//cs.iubenda.com/sync/305777.js"></script>
<script type="text/javascript" src="//cdn.iubenda.com/cs/gpp/stub.js"></script>
<script type="text/javascript" src="//cdn.iubenda.com/cs/iubenda_cs.js" charset="UTF-8" async></script>
"""

IUBENDA_FOOTER = """
      <span class="footer__legal">
        <a href="https://www.iubenda.com/privacy-policy/865793" class="iubenda-white no-brand iubenda-noiframe iubenda-embed" title="Privacy Policy">Privacy Policy</a>
        ·
        <a href="https://www.iubenda.com/privacy-policy/865793/cookie-policy" class="iubenda-white no-brand iubenda-noiframe iubenda-embed" title="Cookie Policy">Cookie Policy</a>
      </span>"""

IUBENDA_LOADER = """
<script type="text/javascript">(function (w,d) {var loader = function () {var s = d.createElement("script"), tag = d.getElementsByTagName("script")[0]; s.src="https://cdn.iubenda.com/iubenda.js"; tag.parentNode.insertBefore(s,tag);}; if(w.addEventListener){w.addEventListener("load", loader, false);}else if(w.attachEvent){w.attachEvent("onload", loader);}else{w.onload = loader;}})(window, document);</script>
"""

MARKER = "_iub.csConfiguration"
VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'
PIVA_FOOTER = '<span class="num">P.IVA 01234567890</span>'
LUCIDE = '<script src="https://unpkg.com/lucide@0.408.0/dist/umd/lucide.min.js"></script>'

SKIP = {"scheda-medico/index.html"}


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    changed = False

    if VIEWPORT in text and MARKER not in text:
        text = text.replace(VIEWPORT, VIEWPORT + IUBENDA_HEAD, 1)
        changed = True

    if PIVA_FOOTER in text and "footer__legal" not in text:
        text = text.replace(
            PIVA_FOOTER,
            PIVA_FOOTER + IUBENDA_FOOTER,
            1,
        )
        changed = True

    if LUCIDE in text and "cdn.iubenda.com/iubenda.js" not in text:
        text = text.replace(LUCIDE, IUBENDA_LOADER + "\n" + LUCIDE, 1)
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
