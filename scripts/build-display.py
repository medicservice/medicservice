#!/usr/bin/env python3
"""Genera i dati del display TV per la sala d'attesa (/display/).

Legge l'elenco medici da medici/index.html, le prestazioni e il link MioDottore
da ogni scheda medici/<slug>/index.html, e produce display/data.js con i QR code
già pronti in SVG (la TV non deve generare nulla né caricare librerie esterne).

Rigenera dopo ogni modifica a medici o servizi:
    pip install qrcode
    python3 scripts/build-display.py
"""

import html
import json
import re
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "display" / "data.js"
PHOTOS_JS = ROOT / "doctor-photos.js"

SITE = "https://medicservice.it"
# I QR portano alla scheda medico sul sito, sezione #prenota: il widget MioDottore
# lì incorporato è legato alla sede di Oristano (anche per i medici con più studi).
# "?tv" marca in Analytics le visite arrivate dalla sala d'attesa; resta corto
# apposta: meno caratteri = QR meno fitto, leggibile da più lontano.
UTM = "?tv"
GENERAL_URL = SITE + "/medici/" + UTM

# Sedi con un proprio display: /display/?sede=<chiave>.
# "escludi" = slug dei medici (cartella in medici/) da non mostrare in quella sede;
# "indirizzo" = testo a piè di pagina (se assente resta Piazza Tharros 57).
# Senza ?sede la pagina mostra tutti i medici.
SEDI = {
    "canalis": {
        "escludi": ["cartagabriele"],
    },
}

# Schermate servizi intercalate tra i medici.
# "agenda" = slug del medico la cui scheda (con widget di prenotazione) apre il QR;
# in alternativa "page" = percorso di una pagina del sito (es. "/medicina-estetica/").
SERVICES = [
    {
        "title": "RX e MOC",
        "eyebrow": "Diagnostica per Immagini",
        "text": "Radiografie e densitometria ossea (MOC-DEXA) in sede, con referto rapido.",
        "items": ["Radiologia tradizionale", "MOC-DEXA", "TAC dentale e ORL"],
        "icon": "scan",
        "agenda": "picciau",
    },
    {
        "title": "Fisioterapia",
        "eyebrow": "Riabilitazione",
        "text": "Percorsi di recupero personalizzati dopo traumi, interventi o dolore cronico.",
        "items": ["Terapia manuale", "Rieducazione funzionale", "Recupero post-operatorio"],
        "icon": "activity",
        "agenda": "concas",
    },
    {
        "title": "Senologia ed ecografia mammaria",
        "eyebrow": "Prevenzione",
        "text": "Visita senologica ed ecografia nello stesso appuntamento.",
        "items": ["Visita senologica", "Ecografia mammaria"],
        "icon": "heart",
        "agenda": "diana",
    },
    {
        "title": "Medicina Estetica",
        "eyebrow": "Viso e corpo",
        "text": "16 trattamenti per viso, corpo e anti-aging, sempre eseguiti da un medico.",
        "items": ["Filler e biostimolazione", "Tossina botulinica", "Trattamenti corpo"],
        "icon": "sparkles",
        "page": "/medicina-estetica/",
    },
]


def load_medici():
    text = (ROOT / "medici" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="medici-data">\s*(\[.*?\])\s*</script>', text, re.S)
    if not m:
        raise SystemExit("medici-data JSON non trovato in medici/index.html")
    return json.loads(m.group(1))


def load_photos():
    text = PHOTOS_JS.read_text(encoding="utf-8")
    return dict(re.findall(r'(\w+):\s*"([^"]+)"', text))


def scheda(slug):
    path = ROOT / "medici" / slug / "index.html"
    if not path.exists():
        return [], None
    text = path.read_text(encoding="utf-8")
    cura = re.search(r'<ul class="cura-list">(.*?)</ul>', text, re.S)
    prest = []
    if cura:
        prest = [html.unescape(s).strip() for s in re.findall(r"</i>\s*([^<]+?)\s*</li>", cura.group(1))]
    has_widget = 'id="prenota"' in text and "zl-url" in text
    return prest, (SITE + "/medici/" + slug + "/" + UTM + "#prenota" if has_widget else None)


def qr_svg(url):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    rows = qr.get_matrix()
    # Un rettangolo per ogni tratto orizzontale di moduli scuri: SVG compatto.
    path = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x]:
                start = x
                while x < len(row) and row[x]:
                    x += 1
                path.append(f"M{start} {y}h{x - start}v1h-{x - start}z")
            else:
                x += 1
    n = len(rows)
    return (
        f'<svg viewBox="0 0 {n} {n}" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
        f'<path d="{"".join(path)}"/></svg>'
    )


def female(display):
    return bool(re.match(r"(Dr\.ssa|Op\.)", display or ""))


def main():
    photos = load_photos()
    agende = {}
    doctors = []
    missing = []
    for d in load_medici():
        slug = d["surname"].lower()
        prest, link = scheda(slug)
        scheda_url = SITE + "/medici/" + slug + "/" + UTM
        if not link:
            missing.append(d["display"])
        agende[slug] = link
        file = photos.get(d["surname"])
        doctors.append({
            "slug": slug,
            "name": d["display"],
            "specs": d["specs"],
            "area": d["catLabels"][0] if d.get("catLabels") else "",
            "prestazioni": prest,
            "photo": "/assets/photos/" + (file or ("generic_medic_female.png" if female(d["display"]) else "generic_medic_male.png")),
            "hasPhoto": bool(file),
            "url": link or scheda_url,
            "direct": bool(link),
            "qr": qr_svg(link or scheda_url),
        })

    services = []
    for s in SERVICES:
        url = agende.get(s.get("agenda")) or SITE + s.get("page", "/medici/") + UTM
        services.append({k: v for k, v in s.items() if k not in ("agenda", "page")} | {"url": url, "qr": qr_svg(url)})

    data = {
        "doctors": doctors,
        "services": services,
        "general": {"url": GENERAL_URL, "qr": qr_svg(GENERAL_URL)},
        "sedi": SEDI,
    }
    slugs = {d["slug"] for d in doctors}
    for nome, sede in SEDI.items():
        for slug in sede.get("escludi", []):
            if slug not in slugs:
                raise SystemExit(f"Sede {nome}: medico '{slug}' non trovato in medici/")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        "/* Generato da scripts/build-display.py — non modificare a mano. */\n"
        "window.DISPLAY_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )
    print(f"{len(doctors)} medici, {len(services)} servizi -> {OUT.relative_to(ROOT)}")
    if missing:
        print("Senza widget di prenotazione (QR alla sola scheda):", ", ".join(missing))


if __name__ == "__main__":
    main()
