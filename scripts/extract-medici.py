#!/usr/bin/env python3
"""Estrae i dati di tutti i medici dalle pagine HTML attuali in data/medici.json.

Solo campi strutturati (niente snapshot HTML). Varianti di layout = campi opzionali.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "medici.json"
PHOTOS_JS = ROOT / "doctor-photos.js"


def load_roster() -> list[dict]:
    text = (ROOT / "medici" / "index.html").read_text(encoding="utf-8")
    m = re.search(
        r'<script type="application/json" id="medici-data">\s*(\[.*?\])\s*</script>',
        text,
        re.S,
    )
    if not m:
        raise SystemExit("medici-data non trovato in medici/index.html")
    return json.loads(m.group(1))


def load_photo_map() -> dict[str, str]:
    text = PHOTOS_JS.read_text(encoding="utf-8")
    m = re.search(r"var PHOTOS = \{([^}]*)\};", text, re.S)
    if not m:
        return {}
    return dict(re.findall(r"(\w+):\s*\"([^\"]+)\"", m.group(1)))


def slugify(surname: str) -> str:
    return surname.lower()


def one(pattern: str, text: str, flags=0) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None


def tags_trail_blank(block: str) -> bool:
    return bool(re.search(r"</span>\n\s*\n\s*$", block))


def extract_scheda(surname: str) -> dict:
    slug = slugify(surname)
    path = ROOT / "medici" / slug / "index.html"
    if not path.exists():
        raise SystemExit(f"Scheda mancante: {path}")
    html = path.read_text(encoding="utf-8")

    photo_src = one(
        r'<div class="doc-hero__photo"><image-slot[^>]*\ssrc="([^"]*)"',
        html,
    ) or ""
    photo_placeholder = one(
        r'<div class="doc-hero__photo"><image-slot[^>]*\splaceholder="([^"]*)"',
        html,
    )
    if photo_placeholder is None:
        photo_placeholder = ""

    stick_spec = one(r'<span class="doc-stickbar__spec">(.*?)</span>', html, re.S) or ""
    stick_spec = re.sub(r"\s+", " ", stick_spec).strip()

    subtitle = one(r'<p class="doc-hero__sub">(.*?)</p>', html, re.S) or ""
    subtitle = re.sub(r"\s+", " ", subtitle).strip()

    hero_tags_m = re.search(
        r'<div class="doc-tags">\n([\s\S]*?)</div>\s*<p class="doc-hero__quote">',
        html,
    )
    if not hero_tags_m:
        hero_tags_m = re.search(
            r'<div class="doc-tags">\n([\s\S]*?)</div>\s*<p class="muted"',
            html,
        )
    hero_tags_block = hero_tags_m.group(1) if hero_tags_m else ""
    hero_tags_list = re.findall(r'<span class="doc-tag">(.*?)</span>', hero_tags_block)
    hero_tags_trail = tags_trail_blank(hero_tags_block) if hero_tags_block else False

    has_quote = 'class="doc-hero__quote"' in html
    quote = ""
    if has_quote:
        quote = (one(r'<p class="doc-hero__quote">(.*?)</p>', html, re.S) or "").strip()

    bios = re.findall(
        r'<p class="muted" style="font-size:16\.5px;max-width:560px;margin-bottom:(\d+)px">(.*?)</p>',
        html,
        re.S,
    )
    bio = [{"text": t.strip(), "marginBottom": int(mb)} for mb, t in bios]

    data_spec = one(r'id="heroSpecIcon"[^>]*\sdata-spec="([^"]*)"', html) or ""
    data_spec_label = one(r'data-spec-label="([^"]*)"', html)

    form_title = one(
        r'<span class="num">01</span>\s*Percorso formativo</span>\s*'
        r'<h2 class="h2" style="color:var\(--navy\);margin:16px 0 30px">(.*?)</h2>',
        html,
        re.S,
    ) or ""
    form_block = one(
        r'<span class="num">01</span>\s*Percorso formativo</span>.*?<ul class="bullets">(.*?)</ul>',
        html,
        re.S,
    ) or ""
    form_items = []
    for li in re.findall(r"<li>(.*?)</li>", form_block, re.S):
        title = (one(r"<b>(.*?)</b>", li, re.S) or "").strip()
        text = one(r"<p>(.*?)</p>", li, re.S)
        item = {"title": title}
        if text is not None:
            item["text"] = text.strip()
        form_items.append(item)

    cura_title = one(
        r'<span class="num">02</span>\s*Cosa curo</span>\s*'
        r'<h2 class="h2" style="color:var\(--navy\);margin:16px 0 30px">(.*?)</h2>',
        html,
        re.S,
    ) or ""
    cura_ul_m = re.search(r'<ul class="cura-list">\n([\s\S]*?)</ul>', html)
    cura_block = cura_ul_m.group(1) if cura_ul_m else ""
    cura_list = [
        re.sub(r"<[^>]+>", "", x).strip()
        for x in re.findall(r"<li>(.*?)</li>", cura_block, re.S)
    ]
    cura_trail = bool(re.search(r"</li>\n[ \t]+\n\s*$", cura_block))

    s3_eyebrow = (one(r'<span class="num">03</span>\s*([^<]+)</span>', html) or "").strip()
    s3_title = one(
        r'<span class="num">03</span>\s*[^<]+</span>\s*'
        r'<h2 class="h2" style="color:var\(--navy\);margin:16px 0 18px">(.*?)</h2>',
        html,
        re.S,
    ) or ""
    m_intro = re.search(
        r'<span class="num">03</span>[\s\S]*?</h2>\s*'
        r'(?:<p class="muted" style="font-size:16px;max-width:620px;margin-bottom:26px">(.*?)</p>\s*)?'
        r'<div class="doc-tags">',
        html,
        re.S,
    )
    s3_intro_text = m_intro.group(1).strip() if m_intro and m_intro.group(1) is not None else None

    s3_tags_m = re.search(
        r'<span class="num">03</span>[\s\S]*?<div class="doc-tags">\n([\s\S]*?)</div>',
        html,
    )
    s3_tags_block = s3_tags_m.group(1) if s3_tags_m else ""
    s3_tags = re.findall(r'<span class="doc-tag">(.*?)</span>', s3_tags_block)
    s3_tags_trail = tags_trail_blank(s3_tags_block) if s3_tags_block else False

    has_prenota = 'id="prenota"' in html
    prenota = None
    if has_prenota:
        prenota_title = one(
            r'<span class="num">04</span>\s*Prenota</span>\s*'
            r'<h2 class="h2" style="color:var\(--navy\);margin:16px 0 24px">(.*?)</h2>',
            html,
            re.S,
        ) or ""
        prenota_text = one(
            r'<span class="num">04</span>\s*Prenota</span>[\s\S]*?'
            r'<p class="muted" style="max-width:360px">(.*?)</p>',
            html,
            re.S,
        ) or ""
        href = one(r'<a id="zl-url"[^>]*\shref="([^"]*)"', html) or ""
        cal_id = one(r'data-zlw-calendar-id="([^"]*)"', html)
        doctor = one(r'data-zlw-doctor="([^"]*)"', html) or ""
        zl = one(r'(<a id="zl-url"[^>]*>Prenota una visita</a>)', html)
        prenota = {
            "title": prenota_title.strip(),
            "text": prenota_text.strip(),
            "miodottore": {"href": href, "doctor": doctor},
        }
        if cal_id is not None:
            prenota["miodottore"]["calendarId"] = cal_id
        if zl:
            prenota["miodottore"]["anchorHtml"] = zl

    cta_title = one(r'ctaband__inner">\s*<div>\s*<h2>(.*?)</h2>', html, re.S) or ""
    cta_text = one(r'ctaband__inner">\s*<div>\s*<h2>.*?</h2>\s*<p>(.*?)</p>', html, re.S) or ""

    stick_m = re.search(
        r'doc-stickbar__inner[\s\S]*?<a class="btn btn--primary" href="([^"]*)"[^>]*>([\s\S]*?)</a>',
        html,
    )
    stick_href = stick_m.group(1) if stick_m else ""
    stick_label = ""
    stick_icon = "calendar-check"
    if stick_m:
        inner = stick_m.group(2)
        stick_icon = one(r'data-lucide="([^"]+)"', inner) or "calendar-check"
        stick_label = re.sub(r"<[^>]+>", "", inner).strip()

    book_btn_label = one(
        r'id="heroCta">\s*<a class="btn btn--primary btn--lg"[^>]*>'
        r'<i data-lucide="[^"]*"></i>\s*([^<]+)</a>',
        html,
        re.S,
    )
    book_btn_label = book_btn_label.strip() if book_btn_label else stick_label

    styles_v = one(r'styles\.css\?v=(\d+)', html) or "9"
    sitejs_v = one(r'site\.js\?v=(\d+)', html) or "6"

    out = {
        "slug": slug,
        "metaTitle": (one(r"<title>(.*?)</title>", html, re.S) or "").strip(),
        "metaDescription": one(r'<meta name="description" content="([^"]*)"', html) or "",
        "stylesVersion": styles_v,
        "siteJsVersion": sitejs_v,
        "photoSrc": photo_src,
        "photoPlaceholder": photo_placeholder,
        "dataSpec": data_spec,
        "subtitle": subtitle,
        "heroTags": hero_tags_list,
        "stickbarSpec": stick_spec,
        "bio": bio,
        "formazione": {"title": form_title.strip(), "items": form_items},
        "cura": {"title": cura_title.strip(), "items": cura_list},
        "competenze": {
            "eyebrow": s3_eyebrow,
            "title": s3_title.strip(),
            "intro": s3_intro_text,
            "tags": s3_tags,
        },
        "prenota": prenota,
        "ctaBand": {"title": cta_title.strip(), "text": cta_text.strip()},
        "stickbar": {"href": stick_href, "icon": stick_icon, "label": stick_label},
        "bookButtonLabel": book_btn_label,
        "layout": {
            "htmlComments": ("===== HEADER" in html) or ("===== DETTAGLIO" in html),
            "prenotaStyle": "#prenota" in html and "scroll-margin-top" in html,
            "resizeScript": "resizeHeight" in html,
            "heroTagsTrailBlank": hero_tags_trail,
            "competenzeTagsTrailBlank": s3_tags_trail,
            "curaTrailBlank": cura_trail,
            "hasQuote": has_quote,
            "stickObserverComment": "STICKY BAR: mostra solo dopo" in html,
            "resizeExtraBlank": bool(
                re.search(r'site\.js\?v=\d+"></script>\n\n\n<script>', html)
            ),
        },
    }
    if "MOBILE DRAWER" in html:
        out["layout"]["drawerCommentLabel"] = "MOBILE DRAWER"
    if data_spec_label is not None:
        out["dataSpecLabel"] = data_spec_label
    if has_quote:
        out["quote"] = quote
    return out


def main() -> None:
    roster = load_roster()
    photo_map = load_photo_map()
    medici = []
    for row in roster:
        surname = row["surname"]
        scheda = extract_scheda(surname)
        photo_file = photo_map.get(surname)
        if photo_file is None and scheda["photoSrc"]:
            name = scheda["photoSrc"].rsplit("/", 1)[-1]
            if name not in ("generic_medic_male.png", "generic_medic_female.png"):
                photo_file = name
        doc = {
            "surname": surname,
            "display": row["display"],
            "specs": row["specs"],
            "cats": row["cats"],
            "catLabels": row["catLabels"],
            **scheda,
        }
        if photo_file:
            doc["photoFile"] = photo_file
        medici.append(doc)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(medici, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scritto {OUT} ({len(medici)} medici)")


if __name__ == "__main__":
    main()
