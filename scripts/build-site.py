#!/usr/bin/env python3
"""Rigenera il sito statico da data/medici.json.

- Completa i campi derivati assenti o null; un valore già scritto resta com'è
- Ordina gli elenchi per cognome, senza distinguere maiuscole e minuscole
- Esclude i medici con "nascosto": true e cancella le schede tolte dal JSON
- Aggiorna i 5 blocchi JSON (home, medici, visite, diagnostica, chirurgia)
- Rigenera le schede con render_scheda_from_fields (template unico)
- Scrive i rimandi medici/<slug-precedente>/ per gli slugPrecedenti dei medici visibili
- Rigenera doctor-photos.js
- Lancia scripts/build-display.py

Uso:
    python3 scripts/build-site.py
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import unicodedata
from copy import deepcopy
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
        "    return /^(Dr\\.ssa|Dott\\.ssa|Op\\.)(\\s|$)/i.test(display || \"\");\n"
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


_TITLE_RE = re.compile(r"^(Dott\.ssa|Dr\.ssa|Dott\.|Dr\.|Op\.)\s+", re.IGNORECASE)
_REQUIRED_TEXT = ("surname", "display", "slug")
_REQUIRED_LISTS = ("specs", "cats", "catLabels")


def _fail(label: str, message: str) -> None:
    raise SystemExit(f"{label}: {message}")


def _medico_label(doc: dict, index: int | None) -> str:
    for key in ("slug", "surname"):
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            name = value.strip()
            break
    else:
        name = ""
    if index is None:
        return name or "medico"
    return f"{name} (#{index + 1})" if name else f"medico #{index + 1}"


def _missing(container: dict, key: str) -> bool:
    return key not in container or container[key] is None


def _fill(container: dict, key: str, value) -> None:
    if _missing(container, key):
        container[key] = value


def _section(doc: dict, key: str, label: str) -> dict:
    if _missing(doc, key):
        doc[key] = {}
    elif not isinstance(doc[key], dict):
        _fail(label, f"{key} deve essere un oggetto")
    return doc[key]


def _require_content(doc: dict, label: str) -> None:
    for key in _REQUIRED_TEXT:
        value = doc.get(key)
        if not isinstance(value, str) or not value.strip():
            _fail(label, f"campo obbligatorio '{key}' mancante o vuoto")
    for key in _REQUIRED_LISTS:
        value = doc.get(key)
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or not item.strip() for item in value)
        ):
            _fail(label, f"campo obbligatorio '{key}' deve essere un elenco di testi")


_CAT_LABELS = {
    "visite": "Visite Specialistiche",
    "diagnostica": "Diagnostica per Immagini",
    "chirurgia": "Chirurgia Day Surgery",
    "estetica": "Medicina Estetica",
}


def _validate_identity(doc: dict, label: str) -> None:
    """slug, surname e coppie cats/catLabels. Si ferma prima di scrivere i file."""
    surname = doc["surname"]
    if not re.fullmatch(r"[A-Za-z]+", surname):
        _fail(
            label,
            "surname può contenere solo lettere a-z e A-Z "
            "(niente spazi, accenti, apostrofi o trattini)",
        )
    expected_slug = surname.lower()
    if doc["slug"] != expected_slug:
        _fail(
            label,
            f"slug '{doc['slug']}' deve essere '{expected_slug}' "
            "(surname in minuscolo): gli elenchi costruiscono i link con surname.toLowerCase()",
        )
    cats = doc["cats"]
    labels = doc["catLabels"]
    if len(cats) != len(labels):
        _fail(
            label,
            f"cats e catLabels hanno lunghezze diverse ({len(cats)} e {len(labels)})",
        )
    for cat, lab in zip(cats, labels):
        expected = _CAT_LABELS.get(cat)
        if expected is None:
            ammessi = ", ".join(_CAT_LABELS)
            _fail(label, f"cat '{cat}' non riconosciuta. Valori ammessi: {ammessi}")
        if lab != expected:
            _fail(
                label,
                f"catLabels non coerente: '{cat}' corrisponde a '{expected}', non a '{lab}'",
            )


def _solo_lettere(testo: str) -> str:
    """Minuscolo, senza accenti, solo a-z. D'Angelo e De Rosa diventano dangelo e derosa."""
    scomposto = unicodedata.normalize("NFD", testo)
    senza_accenti = "".join(c for c in scomposto if unicodedata.category(c) != "Mn")
    return "".join(c for c in senza_accenti.lower() if "a" <= c <= "z")


def _cognome_leggibile(display: str, surname: str) -> str:
    """Cognome come compare nel nome: l'ultima parola, o le ultime due, tre…

    Si prova dal più corto e si tiene il primo gruppo di parole che, senza
    accenti e apostrofi, coincide con surname. Il titolo non entra mai nel
    confronto. Se niente coincide (CartaGabriele) resta l'ultima parola.
    """
    match = _TITLE_RE.match(display)
    nome = display[match.end():] if match else display
    parole = nome.split()
    if not parole:
        pezzi = display.split()
        return pezzi[-1] if pezzi else display
    atteso = surname.lower()
    for n in range(1, len(parole) + 1):
        candidato = " ".join(parole[-n:])
        if _solo_lettere(candidato) == atteso:
            return candidato
    return parole[-1]


def _address_as(display: str, surname: str) -> str:
    """Dr. Sergio Cabras -> il Dr. Cabras; Dr. Marco De Rosa -> il Dr. De Rosa."""
    match = _TITLE_RE.match(display)
    if not match:
        return display
    title = match.group(1)
    short = f"{title} {_cognome_leggibile(display, surname)}"
    folded = title.lower()
    if folded in ("dr.ssa", "dott.ssa"):
        return f"la {short}"
    if folded in ("dr.", "dott."):
        return f"il {short}"
    if folded == "op.":
        return f"l'{short}"
    return short


def _generic_photo(display: str) -> str:
    # Op. finisce con un punto: un word-boundary lì non scatta, quindi si guarda lo spazio.
    if re.match(r"^(Dr\.ssa|Dott\.ssa|Op\.)(\s|$)", display or "", re.IGNORECASE):
        return "generic_medic_female.png"
    return "generic_medic_male.png"


def _default_subtitle(display: str, specs: list[str]) -> str:
    joined = " · ".join(specs)
    if display.startswith("Op."):
        return joined
    return f"Specialista in {joined}"


def _default_stickbar_spec(specs: list[str]) -> str:
    """Con più specialità non ripete la prima: <b>A</b> · B · C. Con una sola: <b>A</b> · A."""
    primary = specs[0]
    rest = specs[1:] if len(specs) > 1 else specs
    return f"<b>{primary}</b> · {' · '.join(rest)}"


def _default_meta_description(display: str, primary: str) -> str:
    spec = primary.lower() if len(primary) > 3 else primary
    return (
        f"{display}, {spec} a Oristano presso Medic Service. "
        "Scopri specializzazioni e prenota online la tua visita."
    )


def _complete_bio(doc: dict, label: str) -> None:
    if "bio" not in doc or doc["bio"] is None:
        return
    bio = doc["bio"]
    if isinstance(bio, str):
        doc["bio"] = [{"text": bio, "marginBottom": 26}]
        return
    if not isinstance(bio, list):
        _fail(label, "bio deve essere un testo o un elenco di paragrafi")
    if not bio:
        return
    needs = False
    for item in bio:
        if not isinstance(item, dict) or _missing(item, "marginBottom") or not isinstance(item.get("text"), str):
            needs = True
            break
    if not needs:
        return
    paragraphs = []
    for index, item in enumerate(bio):
        if isinstance(item, str):
            text = item
            margin = None
        elif isinstance(item, dict):
            text = item.get("text")
            margin = item.get("marginBottom")
        else:
            _fail(label, "ogni paragrafo della bio deve essere un testo o un oggetto")
        if not isinstance(text, str) or not text.strip():
            _fail(label, "ogni paragrafo della bio richiede text")
        if margin is None:
            margin = 26 if index == len(bio) - 1 else 16
        paragraphs.append({"text": text, "marginBottom": margin})
    doc["bio"] = paragraphs


def _complete_string_list(section: dict, key: str, label: str, what: str) -> None:
    if _missing(section, key):
        section[key] = []
        return
    items = section[key]
    if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
        _fail(label, f"{what} deve essere un elenco di testi")


def _complete_formazione_items(form: dict, label: str) -> None:
    if _missing(form, "items"):
        form["items"] = []
        return
    items = form["items"]
    if not isinstance(items, list):
        _fail(label, "formazione.items deve essere un elenco")
    normalized = []
    changed = False
    for item in items:
        if isinstance(item, str):
            normalized.append({"title": item})
            changed = True
            continue
        if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
            _fail(label, "ogni voce di formazione richiede title")
        normalized.append(item)
    if changed:
        form["items"] = normalized


def _complete_prenota(doc: dict, label: str) -> bool:
    """True se c'è il widget. prenota assente o null = nessuna prenotazione online."""
    if "prenota" not in doc or doc["prenota"] is None:
        return False
    prenota = doc["prenota"]
    if not isinstance(prenota, dict):
        _fail(label, "prenota deve essere un oggetto oppure null")
    _fill(prenota, "title", "Scegli data e orario.")
    _fill(
        prenota,
        "text",
        f"Consulta le disponibilità di {doc['display']} e prenota online in pochi passaggi.",
    )
    mio = prenota.get("miodottore")
    if not isinstance(mio, dict):
        _fail(label, "prenota.miodottore richiede href e doctor")
    if not isinstance(mio.get("href"), str) or not mio["href"].strip():
        _fail(label, "prenota.miodottore.href mancante")
    if not isinstance(mio.get("doctor"), str) or not mio["doctor"].strip():
        _fail(label, "prenota.miodottore.doctor mancante")
    if _missing(mio, "anchorHtml"):
        mio["anchorHtml"] = _miodottore_anchor(mio)
    return True


def _complete_layout(doc: dict, has_prenota: bool) -> None:
    layout = _section(doc, "layout", doc.get("slug") or "medico")
    quote = doc.get("quote")
    has_quote = isinstance(quote, str) and bool(quote.strip())
    defaults = {
        "htmlComments": False,
        "prenotaStyle": has_prenota,
        "resizeScript": has_prenota,
        "heroTagsTrailBlank": True,
        "competenzeTagsTrailBlank": False,
        "curaTrailBlank": False,
        "hasQuote": has_quote,
        "stickObserverComment": False,
        "resizeExtraBlank": False,
    }
    for key, value in defaults.items():
        _fill(layout, key, value)


def complete_medico(doc: dict, index: int | None = None) -> dict:
    """Completa i campi derivati. Un valore presente (anche stringa vuota) non si tocca.

    Obbligatori: surname, display, slug, specs, cats, catLabels.
    Contenuto facoltativo: quote, bio, formazione.items, cura.items,
    competenze.tags, competenze.intro, photoFile, prenota
    (null = niente widget; altrimenti miodottore.href, doctor, calendarId).
    """
    if not isinstance(doc, dict):
        _fail(f"medico #{(index or 0) + 1}", "atteso un oggetto")
    doc = deepcopy(doc)
    label = _medico_label(doc, index)
    _require_content(doc, label)
    _validate_identity(doc, label)

    if "quote" in doc and doc["quote"] is not None and not isinstance(doc["quote"], str):
        _fail(label, "quote deve essere un testo")
    if "photoFile" in doc and doc["photoFile"] is not None and not isinstance(doc["photoFile"], str):
        _fail(label, "photoFile deve essere un nome di file")

    _complete_bio(doc, label)

    form = _section(doc, "formazione", label)
    _fill(form, "title", "Una formazione solida.")
    _complete_formazione_items(form, label)

    cura = _section(doc, "cura", label)
    _fill(cura, "title", "Prestazioni e consulenze.")
    _complete_string_list(cura, "items", label, "cura.items")

    comp = _section(doc, "competenze", label)
    _fill(comp, "eyebrow", "Patologie trattate")
    _fill(comp, "title", "Le condizioni che seguo.")
    _complete_string_list(comp, "tags", label, "competenze.tags")

    specs = doc["specs"]
    primary = specs[0]
    display = doc["display"]
    _fill(doc, "dataSpec", primary)
    if _missing(doc, "dataSpecLabel") and len(specs) > 1:
        doc["dataSpecLabel"] = " · ".join(specs)
    _fill(doc, "heroTags", list(specs))
    _fill(doc, "subtitle", _default_subtitle(display, specs))
    _fill(doc, "stickbarSpec", _default_stickbar_spec(specs))
    _fill(doc, "metaTitle", f"{display} — {primary} a Oristano | Medic Service")
    _fill(doc, "metaDescription", _default_meta_description(display, primary))
    _fill(doc, "stylesVersion", "9")
    _fill(doc, "siteJsVersion", "6")
    _fill(doc, "photoPlaceholder", "")
    if _missing(doc, "photoSrc"):
        photo_file = doc.get("photoFile")
        if isinstance(photo_file, str) and photo_file.strip():
            doc["photoSrc"] = "/assets/photos/" + photo_file.strip()
        else:
            doc["photoSrc"] = "/assets/photos/" + _generic_photo(display)

    has_prenota = _complete_prenota(doc, label)
    who = _address_as(display, doc["surname"])
    cta = _section(doc, "ctaBand", label)
    _fill(cta, "title", "Prenota la tua visita")
    _fill(cta, "text", f"Prenoti con {who} in meno di un minuto.")

    book = f"Prenota con {who}" if has_prenota else "Chiama ora"
    _fill(doc, "bookButtonLabel", book)
    stick = _section(doc, "stickbar", label)
    if has_prenota:
        _fill(stick, "href", "#prenota")
        _fill(stick, "icon", "calendar-check")
    else:
        _fill(stick, "href", "tel:0783211136")
        _fill(stick, "icon", "phone")
    _fill(stick, "label", doc["bookButtonLabel"])
    _complete_layout(doc, has_prenota)
    return doc


def complete_medici(medici: list[dict]) -> list[dict]:
    done = []
    slugs: set[str] = set()
    surnames: set[str] = set()
    for index, doc in enumerate(medici):
        full = complete_medico(doc, index)
        if full["slug"] in slugs:
            raise SystemExit(
                f"Slug duplicato '{full['slug']}': in data/medici.json compare più di una volta."
            )
        if full["surname"] in surnames:
            raise SystemExit(
                f"Surname duplicato '{full['surname']}': in data/medici.json compare più di una volta."
            )
        slugs.add(full["slug"])
        surnames.add(full["surname"])
        done.append(full)
    _validate_slug_precedenti(done)
    return done


def _validate_slug_precedenti(medici: list[dict]) -> None:
    """slugPrecedenti, prima di scrivere qualsiasi file.

    Se il campo c'è deve essere un elenco: ogni voce solo a-z minuscolo,
    diversa dallo slug di qualunque medico attuale (anche nascosto) e non
    ripetuta, né nello stesso medico né in un altro.
    """
    attuali = {doc["slug"] for doc in medici}
    visti: dict[str, str] = {}
    for doc in medici:
        if "slugPrecedenti" not in doc:
            continue
        precedenti = doc["slugPrecedenti"]
        label = doc["slug"]
        if not isinstance(precedenti, list):
            _fail(label, "slugPrecedenti deve essere un elenco")
        for voce in precedenti:
            if not isinstance(voce, str) or re.fullmatch(r"[a-z]+", voce) is None:
                _fail(
                    label,
                    f"slugPrecedenti contiene {voce!r}: "
                    "ogni voce può contenere solo lettere minuscole a-z",
                )
            if voce in attuali:
                _fail(
                    label,
                    f"slugPrecedenti '{voce}' coincide con lo slug di un medico attuale "
                    "(visibile o nascosto)",
                )
            altro = visti.get(voce)
            if altro is not None:
                if altro == label:
                    _fail(label, f"slugPrecedenti ripete '{voce}'")
                raise SystemExit(
                    f"slugPrecedenti '{voce}' compare in più medici ({altro} e {label})."
                )
            visti[voce] = label


def _has_text_items(items) -> bool:
    """True se c'è almeno una voce non vuota."""
    if not isinstance(items, list):
        return False
    for item in items:
        if isinstance(item, str):
            if item.strip():
                return True
            continue
        if isinstance(item, dict):
            title = item.get("title")
            if isinstance(title, str) and title.strip():
                return True
            continue
        if item:
            return True
    return False


def _formazione_section(form: dict, num: str, comments: bool) -> str:
    banner = "<!-- ===== DETTAGLIO ===== -->\n" if comments else ""
    note = "        <!-- Percorso formativo -->\n" if comments else ""
    items = _formazione_html(form.get("items") or [])
    return f"""{banner}<section class="section--tight">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
{note}        <div class="reveal">
          <span class="eyebrow"><span class="num">{num}</span> Percorso formativo</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">{form["title"]}</h2>
          <ul class="bullets">
{items}
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>"""


def _cura_section(cura: dict, num: str, trail_blank: bool, comments: bool) -> str:
    banner = "<!-- ===== COSA CURO (full-width grigio) ===== -->\n" if comments else ""
    note = "        <!-- Cosa curo -->\n" if comments else ""
    items = _cura_html(cura.get("items") or [], trail_blank)
    return f"""{banner}<section class="section--tight" style="background:var(--g075)">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
{note}        <div class="reveal">
          <span class="eyebrow"><span class="num">{num}</span> Cosa curo</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">{cura["title"]}</h2>
          <ul class="cura-list">
{items}
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>"""


def _competenze_section(
    comp: dict, num: str, intro_html: str, tags_html: str, comments: bool
) -> str:
    banner = "<!-- ===== PATOLOGIE + NOTA ===== -->\n" if comments else ""
    note = "        <!-- Patologie trattate -->\n" if comments else ""
    # Con i commenti HTML c'è una riga vuota prima della chiusura della colonna.
    gap = "\n" if comments else ""
    return f"""{banner}<section class="section--tight">
  <div class="container">
    <div class="doc-cols" style="grid-template-columns:1fr;max-width:780px">
      <div>
{note}        <div class="reveal">
          <span class="eyebrow"><span class="num">{num}</span> {comp["eyebrow"]}</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 18px">{comp["title"]}</h2>{intro_html}
          <div class="doc-tags">
{tags_html}
          </div>
        </div>
{gap}      </div>
    </div>
  </div>
</section>"""


def _detail_sections(
    form: dict,
    cura: dict,
    comp: dict,
    intro_html: str,
    tags_html: str,
    cura_trail: bool,
    comments: bool,
) -> tuple[str, str]:
    """Solo le sezioni con voci, numerate 01, 02, 03 senza salti.

    Il secondo valore è il numero della sezione Prenota, il successivo.
    """
    blocks: list[str] = []
    number = 1

    def num() -> str:
        nonlocal number
        value = f"{number:02d}"
        number += 1
        return value

    if _has_text_items(form.get("items")):
        blocks.append(_formazione_section(form, num(), comments))
    if _has_text_items(cura.get("items")):
        blocks.append(_cura_section(cura, num(), cura_trail, comments))
    if _has_text_items(comp.get("tags")):
        blocks.append(_competenze_section(comp, num(), intro_html, tags_html, comments))
    html = ("\n\n".join(blocks) + "\n") if blocks else ""
    return html, f"{number:02d}"


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
            '<i data-lucide="phone"></i> Chiama ora</a>'
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

    form_section, prenota_num = _detail_sections(
        form, cura, comp, intro_html, s3_tags, cura_trail, comments
    )

    prenota_section = ""
    if has_prenota:
        anchor = _miodottore_anchor(prenota["miodottore"])
        prenota_section = f"""<!-- ===== PRENOTA (MioDottore calendar) ===== -->
<section class="section--tight" id="prenota" style="background:var(--g075)">
  <div class="container">
    <div class="prenota-wrap">
      <div class="prenota-copy">
        <span class="eyebrow"><span class="num">{prenota_num}</span> Prenota</span>
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
        if form_section:
            prenota_section = "\n" + prenota_section

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
        cta_comment = "\n<!-- ===== CTA BAND ===== -->\n"
        footer_comment = "\n<!-- ===== FOOTER ===== -->\n"
        mobile_comment = "\n<!-- ===== MOBILE STICKY BAR ===== -->\n"
        drawer_label = layout.get("drawerCommentLabel") or "MOBILE DRAWER"
        drawer_comment = f"\n<!-- ===== {drawer_label} ===== -->\n"
    else:
        after_noscript = "\n\n"
        after_header = "\n"
        after_stick = "\n"
        cta_comment = "\n"
        footer_comment = "\n"
        mobile_comment = "\n"
        drawer_comment = "\n"

    if not form_section and not prenota_section:
        cta_comment = cta_comment.lstrip("\n")

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
<link rel="icon" href="/assets/monogram.svg">
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


def _is_hidden(doc: dict) -> bool:
    return doc.get("nascosto") is True


def remove_orphan_schede(keep_slugs: set[str]) -> list[str]:
    """Cancella le schede di medici nascosti o tolti dal JSON.

    Solo le sottocartelle dirette di medici/ che contengono soltanto index.html.
    medici/index.html non è una cartella e non viene toccato.
    keep_slugs include gli slug visibili e gli slugPrecedenti dei medici visibili:
    i rimandi restano, le cartelle dei medici nascosti no.
    """
    root = ROOT / "medici"
    removed: list[str] = []
    if not root.is_dir():
        return removed
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_dir():
            continue
        if path.name in keep_slugs:
            continue
        children = list(path.iterdir())
        only_index = (
            len(children) == 1
            and children[0].is_file()
            and children[0].name == "index.html"
        )
        if not only_index:
            found = ", ".join(sorted(child.name for child in children)) or "(vuota)"
            print(
                f"Non elimino medici/{path.name}/: contiene {found}, non soltanto index.html"
            )
            continue
        children[0].unlink()
        path.rmdir()
        removed.append(path.name)
        print(f"Eliminata scheda medici/{path.name}/")
    return removed


def render_rimando(doc: dict, slug: str) -> str:
    """Pagina minima dal vecchio indirizzo. Nessun GTM e nessuna Iubenda."""
    nome = html.escape(doc["display"])
    destinazione = f"/medici/{slug}/"
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{nome} · Medic Service</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="https://medicservice.it{destinazione}">
<meta http-equiv="refresh" content="0; url={destinazione}">
<script>location.replace("{destinazione}" + location.search + location.hash);</script>
</head>
<body>
<p>La scheda di {nome} è stata spostata: <a href="{destinazione}">vai alla nuova pagina</a>.</p>
</body>
</html>
"""


def write_rimandi(medici: list[dict]) -> int:
    """Per ogni medico visibile, una cartella per ogni slugPrecedenti."""
    n = 0
    for doc in medici:
        for vecchio in doc.get("slugPrecedenti") or []:
            path = ROOT / "medici" / vecchio / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_rimando(doc, doc["slug"]), encoding="utf-8")
            n += 1
    return n


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
    # Validazione e completamento prima di qualsiasi scrittura.
    medici = sorted(complete_medici(load_medici()), key=lambda doc: doc["surname"].casefold())
    visible = [doc for doc in medici if not _is_hidden(doc)]
    hidden = len(medici) - len(visible)
    if hidden:
        print(f"Nascosti, esclusi da elenchi, foto e display: {hidden}")

    rows = roster_payload(visible)
    payload = format_roster_json(rows)

    for path, script_id in ROSTER_TARGETS:
        replace_json_block(path, script_id, payload)
        print(f"JSON aggiornato: {path.relative_to(ROOT)} #{script_id}")

    n = write_schede(visible)
    print(f"Schede scritte: {n} (solo render_scheda_from_fields)")

    n_rimandi = write_rimandi(visible)
    print(f"Rimandi scritti: {n_rimandi}")

    photos_path = ROOT / "doctor-photos.js"
    photos_path.write_text(render_doctor_photos_js(visible), encoding="utf-8")
    print(f"Aggiornato {photos_path.relative_to(ROOT)}")

    keep_slugs = {doc["slug"] for doc in visible}
    for doc in visible:
        keep_slugs.update(doc.get("slugPrecedenti") or [])
    remove_orphan_schede(keep_slugs)

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
