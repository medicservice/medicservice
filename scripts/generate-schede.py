#!/usr/bin/env python3
"""Generate doctor profile pages from the Usai template model."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDICI_HTML = ROOT / "medici.html"
OUT_DIR = ROOT / "medici"

DEFAULT_MIO = "https://www.miodottore.it/strutture/medic-service-oristano"

ANATOMY_ICONS_JS = ROOT / "anatomy-icons.js"
_icons_cache = None


def _load_anatomy_icons():
    text = ANATOMY_ICONS_JS.read_text(encoding="utf-8")

    def parse_string_map(name: str) -> dict[str, str]:
        match = re.search(rf"const {name} = \{{(.*?)\}};", text, re.S)
        if not match:
            return {}
        return dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', match.group(1)))

    icons: dict[str, dict[str, str]] = {}
    icons_match = re.search(r"const ICONS = \{(.*?)\};", text, re.S)
    if icons_match:
        block = icons_match.group(1)
        for key, vb, markup in re.findall(
            r'(\w+):\s*\{\s*vb:\s*"([^"]*)",\s*m:\s*"((?:\\.|[^"\\])*)"\s*\}',
            block,
        ):
            icons[key] = {
                "vb": vb,
                "m": bytes(markup, "utf-8").decode("unicode_escape"),
            }

    return {
        "icons": icons,
        "map": parse_string_map("MAP"),
    }


def _icons() -> dict:
    global _icons_cache
    if _icons_cache is None:
        _icons_cache = _load_anatomy_icons()
    return _icons_cache


def spec_icon_html(spec: str) -> str:
    data = _icons()
    key = data["map"].get(spec)
    ic = data["icons"].get(key) if key else None
    if ic:
        return (
            f'<svg class="health-icon" viewBox="{ic["vb"]}" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">{ic["m"]}</svg>'
        )
    return '<i data-lucide="stethoscope"></i>'


def load_medici():
    text = MEDICI_HTML.read_text(encoding="utf-8")
    match = re.search(r'<script type="application/json" id="medici-data">\s*(\[.*?\])\s*</script>', text, re.S)
    if not match:
        raise SystemExit("medici-data JSON not found in medici.html")
    return json.loads(match.group(1))


def slugify(surname: str) -> str:
    return surname.lower()


def possessive_label(display: str) -> str:
    if display.startswith("Dott.ssa"):
        return "della " + display
    if display.startswith("Dott."):
        return "del " + display
    return "di " + display


def book_label(display: str) -> str:
    if display.startswith("Dott.ssa"):
        return display.replace("Dott.ssa", "la Dott.ssa", 1)
    if display.startswith("Dott."):
        return display.replace("Dott.", "il Dott.", 1)
    return display


def book_btn(display: str, surname: str) -> str:
    if "ssa" in display:
        return f"Prenota con la Dott.ssa {surname}"
    if display.startswith("Dott."):
        return f"Prenota con il Dott. {surname}"
    return f"Prenota con {display}"


def photo_attrs(surname: str) -> tuple[str, str]:
    sid = slugify(surname)
    if surname == "Usai":
        return ' src="../assets/photos/usai.webp"', f'placeholder="Ritratto professionale {surname}"'
    return "", f'placeholder="Ritratto professionale — {surname}"'


def render_page(doc: dict) -> str:
    surname = doc["surname"]
    slug = slugify(surname)
    display = doc["display"]
    specs = doc["specs"]
    primary = specs[0]
    mio = doc.get("mioUrl", DEFAULT_MIO)
    tags = "".join(f'<span class="doc-tag">{s}</span>\n          ' for s in specs[:4])
    cura = "".join(
        f'<li><i data-lucide="check"></i> Visita e consulenza in {s}</li>\n            '
        for s in specs
    )
    patologie = "".join(f'<span class="doc-tag">{s}</span>\n            ' for s in specs)
    stick_specs = " · ".join(specs)
    spec_label_full = stick_specs
    spec_label_attr = f' data-spec-label="{spec_label_full}"' if len(specs) > 1 else ""
    src, ph = photo_attrs(surname)
    bl = book_label(display)
    pl = possessive_label(display)
    btn = book_btn(display, surname)
    title_spec = primary.lower() if len(primary) > 3 else primary

    subtitle = f"Specialista in {primary}" if len(specs) == 1 else f"Specialista in {' · '.join(specs)}"
    if not display.startswith("Dott"):
        subtitle = " · ".join(specs)

    intro = (
        f"{display} riceve presso Medic Service a Oristano. "
        f"Specialità: {', '.join(specs)}. "
        "La scheda completa con percorso formativo, prestazioni e recensioni sarà pubblicata a breve."
    )

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{display} — {primary} a Oristano | Medic Service</title>
<meta name="description" content="{display}, {title_spec} a Oristano presso Medic Service. Scopri specialità e prenota online la tua visita.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Chivo+Mono:wght@300;400;500&family=DM+Serif+Display:ital@0;1&family=Montserrat:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../styles.css?v=3">
</head>
<body data-screen-label="Scheda Medico">

<header class="site-header">
  <div class="container nav">
    <a class="nav__logo" href="../index.html"><img src="../assets/logo-horizontal.svg" alt="Medic Service"></a>
    <nav class="nav__links">
      <a href="../index.html">Home</a>
      <a href="../index.html#aree">Specialità</a>
      <a href="../medici.html" class="active">I Medici</a>
      <a href="../index.html#struttura">La Struttura</a>
    </nav>
    <div class="nav__cta">
      <a class="nav__tel" href="tel:0783211136"><i data-lucide="phone"></i><span class="num">0783 211136</span></a>
      <button class="nav__burger" data-open-drawer aria-label="Menu"><i data-lucide="menu"></i></button>
    </div>
  </div>
</header>

<div class="doc-stickbar" id="docStickbar" aria-hidden="true">
  <div class="container doc-stickbar__inner">
    <div class="doc-stickbar__id">
      <span class="doc-stickbar__photo"><image-slot id="{slug}-portrait"{src} {ph} shape="circle"></image-slot></span>
      <span class="doc-stickbar__txt">
        <span class="doc-stickbar__name">{display}</span>
        <span class="doc-stickbar__spec"><b>{primary}</b> · {stick_specs}</span>
      </span>
    </div>
    <a class="btn btn--primary" href="{mio}" target="_blank" rel="noopener"><i data-lucide="calendar-check"></i> {btn}</a>
  </div>
</div>

<section class="section--tight" id="docHero" style="padding-top:36px">
  <div class="container">
    <nav class="breadcrumb" style="margin-bottom:34px">
      <a href="../index.html">Home</a><i data-lucide="chevron-right"></i>
      <a href="../medici.html">I Medici</a><i data-lucide="chevron-right"></i>
      <span class="cur">{display}</span>
    </nav>
    <div class="doc-hero">
      <div class="doc-hero__photo"><image-slot id="{slug}-portrait"{src} {ph} shape="rect"></image-slot></div>
      <div>
        <span class="eyebrow doc-hero__spec" id="heroSpecIcon" data-spec="{primary}"{spec_label_attr}></span>
        <h1>{display}</h1>
        <p class="doc-hero__sub">{subtitle}</p>
        <div class="doc-tags">
          {tags}
        </div>
        <p class="muted" style="font-size:16.5px;max-width:560px;margin-bottom:26px">{intro}</p>
        <div class="doc-cta" id="heroCta">
          <a class="btn btn--primary btn--lg" href="{mio}" target="_blank" rel="noopener"><i data-lucide="calendar-check"></i> {btn}</a>
          <a class="btn btn--outline btn--lg" href="tel:0783211136"><i data-lucide="phone"></i> Chiama e prenota</a>
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
          <span class="eyebrow"><span class="num">01</span> Percorso formativo</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">In aggiornamento.</h2>
          <ul class="bullets">
            <li>
              <span class="bullets__n">01</span>
              <div><b>Scheda professionale in preparazione</b><p>Il percorso formativo e l'esperienza clinica {pl} saranno pubblicati dopo l'approvazione del professionista.</p></div>
            </li>
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
          <h2 class="h2" style="color:var(--navy);margin:16px 0 30px">Prestazioni e consulenze.</h2>
          <ul class="cura-list">
            {cura}
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
          <span class="eyebrow"><span class="num">03</span> Aree di competenza</span>
          <h2 class="h2" style="color:var(--navy);margin:16px 0 18px">Specialità e ambiti.</h2>
          <p class="muted" style="font-size:16px;max-width:620px;margin-bottom:26px">Elenco indicativo in attesa di approvazione definitiva.</p>
          <div class="doc-tags">
            {patologie}
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="ctaband">
  <div class="ctaband__bg"><img src="../assets/monogram-white.svg" alt=""></div>
  <div class="container ctaband__inner">
    <div>
      <h2>Prenota la tua visita</h2>
      <p>Prenoti con {bl} in meno di un minuto.</p>
    </div>
    <div class="ctaband__actions">
      <a class="btn btn--primary btn--lg" href="{mio}" target="_blank" rel="noopener"><i data-lucide="calendar-check"></i> Prenota online</a>
      <a class="btn btn--ghost-light btn--lg" href="tel:0783211136"><i data-lucide="phone"></i> <span class="num">0783 211136</span></a>
    </div>
  </div>
</section>

<footer class="footer">
  <div class="container">
    <div class="footer__top">
      <div class="footer__brand">
        <img src="../assets/logo-horizontal-white.svg" alt="Medic Service">
        <p>Centro medico polispecialistico nel cuore di Oristano. Cura chiara, professionale, vicina.</p>
        <div class="footer__contact">
          <a href="https://maps.app.goo.gl/DD7feputJqxw9w6r8" target="_blank" rel="noopener"><i data-lucide="map-pin"></i> Piazza Tharros 57, Oristano</a>
          <a href="tel:0783211136"><i data-lucide="phone"></i> <span class="num">0783 211136</span></a>
          <a href="mailto:info@medicservice.it"><i data-lucide="mail"></i> info@medicservice.it</a>
        </div>
      </div>
      <div class="footer__col">
        <h4>Specialità</h4>
        <ul>
          <li><a href="../index.html#aree">Visite Specialistiche</a></li>
          <li><a href="../index.html#aree">Diagnostica per Immagini</a></li>
          <li><a href="../index.html#aree">Chirurgia Day Surgery</a></li>
          <li><a href="../medicina-estetica.html">Medicina Estetica</a></li>
        </ul>
      </div>
      <div class="footer__col">
        <h4>Il centro</h4>
        <ul>
          <li><a href="#">Chi siamo</a></li>
          <li><a href="../medici.html">I medici</a></li>
          <li><a href="../index.html#struttura">La struttura</a></li>
        </ul>
      </div>
    </div>
    <div class="footer__bottom">
      <span>© 2026 Medic Service — Centro Polispecialistico, Oristano</span>
      <span class="num">P.IVA 01234567890</span>
    </div>
  </div>
</footer>

<nav class="mobilebar">
  <a class="mobilebar__book" data-book data-medico="{display} — {primary}"><i data-lucide="calendar-check"></i> Prenota</a>
  <a class="mobilebar__call" href="tel:0783211136"><i data-lucide="phone"></i> <span class="num">0783 211136</span></a>
</nav>

<div class="drawer">
  <div class="drawer__scrim"></div>
  <div class="drawer__panel">
    <button class="drawer__close" data-close-drawer aria-label="Chiudi"><i data-lucide="x"></i></button>
    <a href="../index.html">Home</a>
    <a href="../index.html#aree">Specialità</a>
    <a href="../medici.html">I Medici</a>
    <a href="../index.html#struttura">La Struttura</a>
    <a href="../medicina-estetica.html">Medicina Estetica</a>
    <button class="btn btn--primary btn--block" data-book data-medico="{display} — {primary}" style="margin-top:20px" data-close-drawer>Prenota online</button>
  </div>
</div>

<script src="https://unpkg.com/lucide@0.408.0/dist/umd/lucide.min.js"></script>
<script src="../anatomy-icons.js?v=8"></script>
<script src="../image-slot.js"></script>
<script src="../site.js"></script>
<script>
(function () {{
  const hero = document.getElementById("heroCta");
  const bar = document.getElementById("docStickbar");
  if (!hero || !bar) return;
  const io = new IntersectionObserver((entries) => {{
    entries.forEach((e) => {{
      const passed = !e.isIntersecting;
      bar.classList.toggle("show", passed);
      bar.setAttribute("aria-hidden", passed ? "false" : "true");
    }});
  }}, {{ rootMargin: "-76px 0px 0px 0px", threshold: 0 }});
  io.observe(hero);
}})();
</script>
</body>
</html>
"""


def main():
    medici = load_medici()
    OUT_DIR.mkdir(exist_ok=True)
    created = 0
    for doc in medici:
        slug = slugify(doc["surname"])
        out = OUT_DIR / f"{slug}.html"
        if slug == "usai":
            continue  # hand-crafted model page
        out.write_text(render_page(doc), encoding="utf-8")
        created += 1
    print(f"Generated {created} doctor pages in {OUT_DIR}")


if __name__ == "__main__":
    main()
