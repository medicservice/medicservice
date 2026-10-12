#!/usr/bin/env python3
"""Rigenera il sito statico da data/medici.json.

- Aggiorna i 5 blocchi JSON (home, medici, visite, diagnostica, chirurgia)
- Rigenera le 48 schede con render_scheda_from_fields (template unico)
- Rigenera doctor-photos.js
- Lancia scripts/build-display.py

Uso:
    python3 scripts/build-site.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "medici.json"

ROSTER_TARGETS = [
    (ROOT / "index.html", "home-medici-data"),
    (ROOT / "medici" / "index.html", "medici-data"),
    (ROOT / "visite-specialistiche" / "index.html", "roster"),
    (ROOT / "diagnostica" / "index.html", "roster"),
    (ROOT / "chirurgia" / "index.html", "roster"),
]

PRENOTA_STYLE = """<style>
  #prenota {
    scroll-margin-top: 96px;
    overflow: visible;
    padding-bottom: 80px;
  }
  .prenota-wrap {
    display: grid;
    gap: 28px;
    align-items: start;
    overflow: visible;
  }
  .prenota-copy { max-width: 420px; }
  .md-calendar {
    margin-top: 8px;
    width: 100%;
    max-width: 420px;
    overflow: visible;
    min-height: 780px;
  }
  .md-calendar iframe {
    display: block;
    width: 100% !important;
    max-width: none;
    border: 0;
    overflow: visible !important;
    min-height: 780px !important;
  }
  @media (min-width: 1024px) {
    .prenota-wrap {
      grid-template-columns: minmax(0, 420px) minmax(400px, 420px);
      justify-content: start;
      gap: 24px;
    }
    .md-calendar { margin-top: 0; justify-self: start; }
  }
</style>
"""

RESIZE_SCRIPT = """<script>
(function () {
  window.addEventListener("message", function (event) {
    var data = event.data;
    if (typeof data === "string") {
      try { data = JSON.parse(data); } catch (e) { return; }
    }
    if (!data || typeof data !== "object") return;
    var height = data.height || data.resizeHeight;
    if (!height || !data.id) return;
    var iframe = document.querySelector('.md-calendar iframe[data-id="' + data.id + '"]')
      || document.querySelector(".md-calendar iframe");
    if (!iframe) return;
    var h = Math.max(Number(height) + 24, 780);
    iframe.style.height = h + "px";
  });
})();
</script>
"""

STICK_OBSERVER = """<script>
(function () {
  const hero = document.getElementById("heroCta");
  const bar = document.getElementById("docStickbar");
  if (!hero || !bar) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      const passed = !e.isIntersecting;
      bar.classList.toggle("show", passed);
      bar.setAttribute("aria-hidden", passed ? "false" : "true");
    });
  }, { rootMargin: "-76px 0px 0px 0px", threshold: 0 });
  io.observe(hero);
})();
</script>
"""


def load_medici() -> list[dict]:
    if not DATA.exists():
        raise SystemExit(f"Manca {DATA}: esegui prima scripts/extract-medici.py")
    return json.loads(DATA.read_text(encoding="utf-8"))


def roster_payload(medici: list[dict]) -> list[dict]:
    return [
        {
            "surname": d["surname"],
            "display": d["display"],
            "specs": d["specs"],
            "cats": d["cats"],
            "catLabels": d["catLabels"],
        }
        for d in medici
    ]


def format_roster_json(rows: list[dict]) -> str:
    body = ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows)
    return "[" + body + "]\n"


def replace_json_block(path: Path, script_id: str, payload: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = rf'(<script type="application/json" id="{script_id}">\s*)(\[.*?\])(\s*</script>)'
    new_text, n = re.subn(pattern, rf"\g<1>{payload.rstrip()}\g<3>", text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"Blocco {script_id} non trovato in {path}")
    path.write_text(new_text, encoding="utf-8")


def render_doctor_photos_js(medici: list[dict]) -> str:
    entries = [(d["surname"], d["photoFile"]) for d in medici if d.get("photoFile")]
    preferred = [
        "Usai", "Cabula", "Cabras", "Cadeddu", "Canu", "CartaGabriele", "Carta",
        "Corona", "Diana", "Oppo", "Paderi", "Pibi", "Picciau", "Pintor", "Pitzalis",
        "Salfi", "Spiga", "Trincas", "Concas", "Fornero", "Humaidan", "Maleddu",
        "Melis", "Monni", "Mirai", "Onali",
    ]
    by_surname = dict(entries)
    ordered = []
    seen = set()
    for key in preferred:
        if key in by_surname:
            ordered.append((key, by_surname[key]))
            seen.add(key)
    for s, f in entries:
        if s not in seen:
            ordered.append((s, f))
            seen.add(s)
    body = ",\n".join(f"    {s}: \"{f}\"" for s, f in ordered)
    return (
        "(function (global) {\n"
        "  var PHOTOS = {\n"
        f"{body},\n"
        "  };\n"
        "\n"
        "  function isFemaleDoctor(display) {\n"
        "    return /^(Dr\\.ssa|Op\\.)\\b/i.test(display || \"\");\n"
        "  }\n"
        "\n"
        "  function doctorPhotoSrc(surname, display, prefix) {\n"
        "    prefix = prefix || \"/assets/photos/\";\n"
        "    var file = PHOTOS[surname];\n"
        "    if (file) return prefix + file;\n"
        "    return prefix + (isFemaleDoctor(display) ? \"generic_medic_female.png\" : \"generic_medic_male.png\");\n"
        "  }\n"
        "\n"
        "  global.doctorPhotoSrc = doctorPhotoSrc;\n"
        "  global.isFemaleDoctor = isFemaleDoctor;\n"
        "})((typeof window !== \"undefined\" && window) || globalThis);\n"
    )


def _tags_html(tags: list[str], indent: str, trail_blank: bool) -> str:
    lines = [f'{indent}<span class="doc-tag">{t}</span>' for t in tags]
    if trail_blank:
        lines.append(indent.rstrip() and indent or indent)  # keep indent spaces on blank line
        # blank line with same indent spaces stripped to trailing spaces only
        lines[-1] = indent  # line with only indentation spaces
    return "\n".join(lines)


def _formazione_html(items: list[dict]) -> str:
    parts = []
    for i, item in enumerate(items, 1):
        n = f"{i:02d}"
        if item.get("text"):
            inner = f"<b>{item['title']}</b><p>{item['text']}</p>"
        else:
            inner = f"<b>{item['title']}</b>"
        parts.append(
            f"""            <li>
              <span class="bullets__n">{n}</span>
              <div>{inner}</div>
            </li>"""
        )
    return "\n".join(parts)


def _cura_html(items: list[str], trail_blank: bool = False) -> str:
    lines = [f'            <li><i data-lucide="check"></i> {it}</li>' for it in items]
    if trail_blank:
        lines.append("            ")
    return "\n".join(lines)


def _bio_html(bio: list) -> str:
    """bio: list of {text, marginBottom} or legacy list of strings."""
    if not bio:
        return ""
    parts = []
    for i, item in enumerate(bio):
        if isinstance(item, dict):
            text = item["text"]
            mb = item.get("marginBottom", 26 if i == len(bio) - 1 else 16)
        else:
            text = item
            mb = 26 if i == len(bio) - 1 else 16
            if len(bio) == 1:
                mb = 26
        parts.append(
            f'<p class="muted" style="font-size:16.5px;max-width:560px;margin-bottom:{mb}px">{text}</p>'
        )
    return "\n        ".join(parts)


def _miodottore_anchor(mio: dict) -> str:
    if mio.get("anchorHtml"):
        return mio["anchorHtml"]
    attrs = [f'href="{mio["href"]}"', 'rel="nofollow"']
    if mio.get("calendarId"):
        attrs.append(f'data-zlw-calendar-id="{mio["calendarId"]}"')
    attrs.extend(
        [
            f'data-zlw-doctor="{mio["doctor"]}"',
            'data-zlw-type="big_with_calendar"',
            'data-zlw-opinion="false"',
            'data-zlw-hide-branding="true"',
            'data-zlw-saas-only="false"',
            'data-zlw-a11y-title="Widget di prenotazione visite mediche"',
        ]
    )
    return f'<a id="zl-url" class="zl-url" {" ".join(attrs)}>Prenota una visita</a>'


def render_scheda_from_fields(doc: dict) -> str:
    """Template unico: gestisce tutte le varianti tramite campi in medici.json."""
    slug = doc["slug"]
    display = doc["display"]
    prenota = doc.get("prenota")
    has_prenota = prenota is not None
    layout = doc.get("layout") or {}
    comments = bool(layout.get("htmlComments"))

    photo = doc.get("photoSrc") or "/assets/photos/generic_medic_male.png"
    ph = doc.get("photoPlaceholder", "")
    data_spec = doc.get("dataSpec") or (doc["specs"][0] if doc.get("specs") else "")
    label_attr = f' data-spec-label="{doc["dataSpecLabel"]}"' if doc.get("dataSpecLabel") else ""

    styles_v = doc.get("stylesVersion") or "9"
    sitejs_v = doc.get("siteJsVersion") or "6"

    hero_trail = bool(layout.get("heroTagsTrailBlank", True))
    s3_trail = bool(layout.get("competenzeTagsTrailBlank", False))
    cura_trail = bool(layout.get("curaTrailBlank", False))
    hero_tags = _tags_html(doc.get("heroTags") or doc.get("specs") or [], "          ", hero_trail)

    stick_spec = doc.get("stickbarSpec") or f"<b>{doc['specs'][0]}</b>"
    stick = doc.get("stickbar") or {}
    stick_href = stick.get("href") or ("#prenota" if has_prenota else "tel:0783211136")
    stick_icon = stick.get("icon") or ("calendar-check" if has_prenota else "phone")
    stick_label = stick.get("label") or doc.get("bookButtonLabel") or "Prenota"
    book_label = doc.get("bookButtonLabel") or stick_label

    if has_prenota:
        hero_cta = (
            f'          <a class="btn btn--primary btn--lg" href="#prenota">'
            f'<i data-lucide="calendar-check"></i> {book_label}</a>\n'
            f'          <a class="btn btn--outline btn--lg" href="tel:0783211136">'
            f'<i data-lucide="phone"></i> Chiama e prenota</a>'
        )
        cta_actions = (
            '      <a class="btn btn--primary btn--lg" href="#prenota">'
            '<i data-lucide="calendar-check"></i> Prenota online</a>\n'
            '      <a class="btn btn--ghost-light btn--lg" href="tel:0783211136">'
            '<i data-lucide="phone"></i> <span class="num">0783 211136</span></a>'
        )
        mobile_book = (
            '<a class="mobilebar__book" href="#prenota">'
            '<i data-lucide="calendar-check"></i> Prenota</a>'
        )
        drawer_cta = (
            '<a class="btn btn--primary btn--block" href="#prenota" '
            'style="margin-top:20px" data-close-drawer>Prenota online</a>'
        )
    else:
        hero_cta = (
            f'          <a class="btn btn--primary btn--lg" href="tel:0783211136">'
            f'<i data-lucide="phone"></i> {book_label}</a>'
        )
        cta_actions = (
            '      <a class="btn btn--primary btn--lg" href="tel:0783211136">'
            '<i data-lucide="phone"></i> Chiama ora</a>\n'
            '      <a class="btn btn--ghost-light btn--lg" href="tel:0783211136">'
            '<i data-lucide="phone"></i> <span class="num">0783 211136</span></a>'
        )
        mobile_book = (
            '<a class="mobilebar__book" href="tel:0783211136">'
            '<i data-lucide="phone"></i> Chiama ora</a>'
        )
        drawer_cta = (
            '<a class="btn btn--primary btn--block" href="tel:0783211136" '
            'style="margin-top:20px" data-close-drawer>'
            '<i data-lucide="phone"></i> Chiama ora</a>'
        )

    form = doc.get("formazione") or {"title": "Una formazione solida.", "items": []}
    cura = doc.get("cura") or {"title": "Prestazioni e consulenze.", "items": []}
    comp = doc.get("competenze") or {
        "eyebrow": "Patologie trattate",
        "title": "Le condizioni che seguo.",
        "intro": None,
        "tags": [],
    }

    intro_html = ""
    if comp.get("intro") is not None:
        intro_html = (
            f'\n          <p class="muted" style="font-size:16px;max-width:620px;'
            f'margin-bottom:26px">{comp["intro"]}</p>'
        )

    s3_tags = _tags_html(comp.get("tags") or [], "            ", s3_trail)

    quote_html = ""
    if layout.get("hasQuote", "quote" in doc):
        quote_html = f'\n        <p class="doc-hero__quote">{doc.get("quote") or ""}</p>'

    bios = _bio_html(doc.get("bio") or [])
    bio_block = f"\n        {bios}" if bios else ""

    prenota_section = ""
    if has_prenota:
        anchor = _miodottore_anchor(prenota["miodottore"])
        prenota_section = f"""
<!-- ===== PRENOTA (MioDottore calendar) ===== -->
<section class="section--tight" id="prenota" style="background:var(--g075)">
  <div class="container">
    <div class="prenota-wrap">
      <div class="prenota-copy">
        <span class="eyebrow"><span class="num">04</span> Prenota</span>
        <h2 class="h2" style="color:var(--navy);margin:16px 0 24px">{prenota["title"]}</h2>
        <p class="muted" style="max-width:360px">{prenota["text"]}</p>
      </div>
      <div class="md-calendar">
        {anchor}
        <script>!function($_x,_s,id){{var js,fjs=$_x.getElementsByTagName(_s)[0];if(!$_x.getElementById(id)){{js = $_x.createElement(_s);js.id = id;js.src = "//platform.docplanner.com/js/widget.js";fjs.parentNode.insertBefore(js,fjs);}}}}(document,"script","zl-widget-s");</script>
      </div>
    </div>
  </div>
</section>
"""

    style_block = ""
    if layout.get("prenotaStyle") or has_prenota:
        # pages without prenota never include the style block
        if has_prenota:
            style_block = PRENOTA_STYLE

    cta = doc.get("ctaBand") or {"title": "Prenota la tua visita", "text": ""}

    if comments:
        # già c'è un \n a fine riga del commento noscript / </header> / </div>
        after_noscript = "\n\n<!-- ===== HEADER ===== -->\n"
        after_header = "\n<!-- ===== STICKY BAR MEDICO (appare dopo la prima sezione) ===== -->\n"
        after_stick = "\n<!-- ===== DOCTOR HERO ===== -->\n"
        form_section = f"""<!-- ===== DETTAGLIO ===== -->
<section class="section--tight">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
        <!-- Percorso formativo -->
        <div class="reveal">
          <span class="eyebrow"><span class="num">01</span> Percorso formativo</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">{form["title"]}</h2>
          <ul class="bullets">
{_formazione_html(form.get("items") or [])}
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ===== COSA CURO (full-width grigio) ===== -->
<section class="section--tight" style="background:var(--g075)">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
        <!-- Cosa curo -->
        <div class="reveal">
          <span class="eyebrow"><span class="num">02</span> Cosa curo</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">{cura["title"]}</h2>
          <ul class="cura-list">
{_cura_html(cura.get("items") or [], cura_trail)}
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ===== PATOLOGIE + NOTA ===== -->
<section class="section--tight">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
        <!-- Patologie trattate -->
        <div class="reveal">
          <span class="eyebrow"><span class="num">03</span> {comp["eyebrow"]}</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 18px">{comp["title"]}</h2>{intro_html}
          <div class="doc-tags">
{s3_tags}
          </div>
        </div>

      </div>
    </div>
  </div>
</section>
"""
        cta_comment = "\n<!-- ===== CTA BAND ===== -->\n"
        footer_comment = "\n<!-- ===== FOOTER ===== -->\n"
        mobile_comment = "\n<!-- ===== MOBILE STICKY BAR ===== -->\n"
        drawer_label = layout.get("drawerCommentLabel") or "MOBILE DRAWER"
        drawer_comment = f"\n<!-- ===== {drawer_label} ===== -->\n"
    else:
        after_noscript = "\n\n"
        after_header = "\n"
        after_stick = "\n"
        form_section = f"""<section class="section--tight">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
        <div class="reveal">
          <span class="eyebrow"><span class="num">01</span> Percorso formativo</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">{form["title"]}</h2>
          <ul class="bullets">
{_formazione_html(form.get("items") or [])}
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section--tight" style="background:var(--g075)">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
        <div class="reveal">
          <span class="eyebrow"><span class="num">02</span> Cosa curo</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">{cura["title"]}</h2>
          <ul class="cura-list">
{_cura_html(cura.get("items") or [], cura_trail)}
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section--tight">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
        <div class="reveal">
          <span class="eyebrow"><span class="num">03</span> {comp["eyebrow"]}</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 18px">{comp["title"]}</h2>{intro_html}
          <div class="doc-tags">
{s3_tags}
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
"""
        cta_comment = "\n"
        footer_comment = "\n"
        mobile_comment = "\n"
        drawer_comment = "\n"

    resize = ""
    if has_prenota and (layout.get("resizeScript", True)):
        # blank line after site.js (usai: due), then resize, then blank before stick observer
        lead = "\n\n" if layout.get("resizeExtraBlank") else "\n"
        resize = f"{lead}{RESIZE_SCRIPT}\n"

    stick_obs_comment = ""
    if layout.get("stickObserverComment"):
        # resize già termina con blank line; qui solo il commento + newline
        stick_obs_comment = (
            "<!-- ===== STICKY BAR: mostra solo dopo aver superato la prima sezione ===== -->\n"
        )

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','GTM-TKGKM6ZJ');</script>
<!-- End Google Tag Manager -->

<link rel="canonical" href="https://medicservice.it/medici/{slug}/">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Iubenda Cookie Solution -->
<script type="text/javascript">
var _iub = _iub || [];
_iub.csConfiguration = {{"askConsentAtCookiePolicyUpdate":true,"countryDetection":true,"emailMarketing":{{"theme":"dark"}},"enableFadp":true,"enableLgpd":true,"enableUspr":true,"lgpdAppliesGlobally":false,"perPurposeConsent":true,"siteId":305777,"whitelabel":false,"cookiePolicyId":865793,"lang":"it","googleConsentMode":"template","emitGtmEvents":true,"floatingPreferencesButtonDisplay":"bottom-right","floatingPreferencesButtonRound":true,"floatingPreferencesButtonHover":true,"banner":{{"acceptButtonDisplay":true,"closeButtonRejects":true,"customizeButtonDisplay":true,"explicitWithdrawal":true,"fontSizeBody":"12px","listPurposes":true,"logo":null,"ownerName":"medicservice.it","position":"float-bottom-right","rejectButtonDisplay":true,"showPurposesToggles":true,"showTotalNumberOfProviders":true}}}};
_iub.csLangConfiguration = {{"it":{{"cookiePolicyId":865793}}}};
</script>
<script type="text/javascript" src="//cs.iubenda.com/sync/305777.js"></script>
<script type="text/javascript" src="//cdn.iubenda.com/cs/gpp/stub.js"></script>
<script type="text/javascript" src="//cdn.iubenda.com/cs/iubenda_cs.js" charset="UTF-8" async></script>


<title>{doc.get("metaTitle") or display}</title>
<meta name="description" content="{doc.get("metaDescription") or ""}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Chivo+Mono:wght@300;400;500&family=DM+Serif+Display:ital@0;1&family=Montserrat:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css?v={styles_v}">
{style_block}</head>
<body data-screen-label="Scheda Medico">
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-TKGKM6ZJ"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
{after_noscript}<header class="site-header">
  <div class="container nav">
    <a class="nav__logo" href="/"><img src="/assets/logo-horizontal.svg" alt="Medic Service"></a>
    <nav class="nav__links">
      <a href="/">Home</a>
      <a href="/#aree">Specializzazioni</a>
      <a href="/medici/" class="active">I Medici</a>
      <a href="/#struttura">La Struttura</a>
    </nav>
    <div class="nav__cta">
      <a class="nav__tel" href="tel:0783211136"><i data-lucide="phone"></i><span class="num">0783 211136</span></a>
      <button class="nav__burger" data-open-drawer aria-label="Menu"><i data-lucide="menu"></i></button>
    </div>
  </div>
</header>
{after_header}<div class="doc-stickbar" id="docStickbar" aria-hidden="true">
  <div class="container doc-stickbar__inner">
    <div class="doc-stickbar__id">
      <span class="doc-stickbar__photo"><image-slot id="{slug}-portrait" placeholder="" src="{photo}" shape="circle"></image-slot></span>
      <span class="doc-stickbar__txt">
        <span class="doc-stickbar__name">{display}</span>
        <span class="doc-stickbar__spec">{stick_spec}</span>
      </span>
    </div>
    <a class="btn btn--primary" href="{stick_href}"><i data-lucide="{stick_icon}"></i> {stick_label}</a>
  </div>
</div>
{after_stick}<section class="section--tight" id="docHero" style="padding-top:36px">
  <div class="container">
    <nav class="breadcrumb" style="margin-bottom:34px">
      <a href="/">Home</a><i data-lucide="chevron-right"></i>
      <a href="/medici/">I Medici</a><i data-lucide="chevron-right"></i>
      <span class="cur">{display}</span>
    </nav>
    <div class="doc-hero">
      <div class="doc-hero__photo"><image-slot id="{slug}-portrait" placeholder="{ph}" src="{photo}" shape="rect"></image-slot></div>
      <div>
        <span class="eyebrow doc-hero__spec" id="heroSpecIcon" data-spec="{data_spec}"{label_attr}></span>
        <h1>{display}</h1>
        <p class="doc-hero__sub">{doc.get("subtitle") or ""}</p>
        <div class="doc-tags">
{hero_tags}
        </div>{quote_html}{bio_block}
        <div class="doc-cta" id="heroCta">
{hero_cta}
        </div>
      </div>
    </div>
  </div>
</section>

{form_section}{prenota_section}{cta_comment}<section class="ctaband">
  <div class="ctaband__bg"><img src="/assets/monogram-white.svg" alt=""></div>
  <div class="container ctaband__inner">
    <div>
      <h2>{cta.get("title") or "Prenota la tua visita"}</h2>
      <p>{cta.get("text") or ""}</p>
    </div>
    <div class="ctaband__actions">
{cta_actions}
    </div>
  </div>
</section>
{footer_comment}<footer class="footer">
  <div class="container">
    <div class="footer__top">
      <div class="footer__brand">
        <img src="/assets/logo-horizontal-white.svg" alt="Medic Service">
        <p>Centro medico polispecialistico nel cuore di Oristano. Cura chiara, professionale, vicina.</p>
        <div class="footer__contact">
          <a href="https://maps.app.goo.gl/DD7feputJqxw9w6r8" target="_blank" rel="noopener"><i data-lucide="map-pin"></i> Piazza Tharros 57, Oristano</a>
          <a href="tel:0783211136"><i data-lucide="phone"></i> <span class="num">0783 211136</span></a>
          <a href="mailto:info@medicservice.it"><i data-lucide="mail"></i> info@medicservice.it</a>
        </div>
      </div>
      <div class="footer__col">
        <h4>Specializzazioni</h4>
        <ul>
          <li><a href="/#aree">Visite Specialistiche</a></li>
          <li><a href="/#aree">Diagnostica per Immagini</a></li>
          <li><a href="/#aree">Chirurgia Day Surgery</a></li>
          <li><a href="/medicina-estetica/">Medicina Estetica</a></li>
        </ul>
      </div>
      <div class="footer__col">
        <h4>Il centro</h4>
        <ul>
          <li><a href="/medici/">I medici</a></li>
          <li><a href="/#struttura">La struttura</a></li>
        </ul>
      </div>
    </div>
    <div class="footer__bottom">
      <span>© 2026 Medic Service — Centro Polispecialistico, Oristano</span>
      <span>Direttore Sanitario: <b>Dottor Augusto Cadeddu</b></span>
      <span class="num">P.IVA 01019170958</span>
      <span class="footer__legal">
        <a href="https://www.iubenda.com/privacy-policy/865793" class="iubenda-white no-brand iubenda-noiframe iubenda-embed" title="Privacy Policy">Privacy Policy</a>
        ·
        <a href="https://www.iubenda.com/privacy-policy/865793/cookie-policy" class="iubenda-white no-brand iubenda-noiframe iubenda-embed" title="Cookie Policy">Cookie Policy</a>
      </span>
    </div>
  </div>
</footer>
{mobile_comment}<nav class="mobilebar">
  {mobile_book}
  <a class="mobilebar__call" href="tel:0783211136"><i data-lucide="phone"></i> <span class="num">0783 211136</span></a>
</nav>
{drawer_comment}<div class="drawer">
  <div class="drawer__scrim"></div>
  <div class="drawer__panel">
    <button class="drawer__close" data-close-drawer aria-label="Chiudi"><i data-lucide="x"></i></button>
    <a href="/">Home</a>
    <a href="/#aree">Specializzazioni</a>
    <a href="/medici/">I Medici</a>
    <a href="/#struttura">La Struttura</a>
    <a href="/medicina-estetica/">Medicina Estetica</a>
    {drawer_cta}
  </div>
</div>


<script type="text/javascript">(function (w,d) {{var loader = function () {{var s = d.createElement("script"), tag = d.getElementsByTagName("script")[0]; s.src="https://cdn.iubenda.com/iubenda.js"; tag.parentNode.insertBefore(s,tag);}}; if(w.addEventListener){{w.addEventListener("load", loader, false);}}else if(w.attachEvent){{w.attachEvent("onload", loader);}}else{{w.onload = loader;}}}})(window, document);</script>

<script src="https://unpkg.com/lucide@0.408.0/dist/umd/lucide.min.js"></script>
<script src="/anatomy-icons.js?v=8"></script>
<script src="/image-slot.js?v=2"></script>
<script src="/site.js?v={sitejs_v}"></script>
{resize}{stick_obs_comment}{STICK_OBSERVER}</body>
</html>
"""
    return html


def render_scheda(doc: dict) -> str:
    """Unico punto di generazione scheda: sempre dai campi strutturati."""
    return render_scheda_from_fields(doc)


def write_schede(medici: list[dict]) -> int:
    for doc in medici:
        if "html" in doc:
            raise SystemExit(
                f"Trovato campo 'html' in {doc.get('slug')}: rimuovilo da medici.json"
            )
        path = ROOT / "medici" / doc["slug"] / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_scheda(doc), encoding="utf-8")
    return len(medici)


def main() -> None:
    medici = load_medici()
    rows = roster_payload(medici)
    payload = format_roster_json(rows)

    for path, script_id in ROSTER_TARGETS:
        replace_json_block(path, script_id, payload)
        print(f"JSON aggiornato: {path.relative_to(ROOT)} #{script_id}")

    n = write_schede(medici)
    print(f"Schede scritte: {n} (solo render_scheda_from_fields)")

    photos_path = ROOT / "doctor-photos.js"
    photos_path.write_text(render_doctor_photos_js(medici), encoding="utf-8")
    print(f"Aggiornato {photos_path.relative_to(ROOT)}")

    display_script = ROOT / "scripts" / "build-display.py"
    print("Eseguo build-display.py…")
    env = dict(os.environ)
    local_qr = ROOT / ".pip-qrcode"
    if local_qr.is_dir():
        env["PYTHONPATH"] = str(local_qr) + (
            (":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else ""
        )
    subprocess.check_call([sys.executable, str(display_script)], cwd=ROOT, env=env)
    print("Fatto.")


if __name__ == "__main__":
    main()
