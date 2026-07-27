#!/usr/bin/env python3
"""Migrate site to clean URLs (folder/index.html) for GitHub Pages."""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://medicservice.it"

ROOT_PAGES = [
    "medici",
    "visite-specialistiche",
    "diagnostica",
    "chirurgia",
    "medicina-estetica",
    "struttura",
]

TEXT_SUFFIXES = {".html", ".js", ".py", ".jsx", ".css", ".md"}


def transform_content(text: str) -> str:
    # JS URL builders
    text = text.replace(
        '"/medici/" + d.surname.toLowerCase() + "/"',
        '"/medici/" + d.surname.toLowerCase() + "/"',
    )
    text = text.replace('"/medicina-estetica/"', '"/medicina-estetica/"')

    # Query links on medici listing
    text = re.sub(r"medici\.html(\?)", r"/medici/\1", text)

    # Doctor profile pages
    text = re.sub(r"(?:\.\./)?medici/([a-z0-9-]+)\.html", r"/medici/\1/", text)

    # Section pages
    for page in ROOT_PAGES + ["mobile", "scheda-medico", "scheda-medico-print"]:
        text = re.sub(rf"(?:\.\./)?{re.escape(page)}\.html", f"/{page}/", text)

    # Home + anchors
    text = re.sub(r'(?:\.\./)?index\.html(#)', r"/\1", text)
    text = re.sub(r'(?:\.\./)?index\.html(?=["\'\s>?])', "/", text)

    # Root-relative assets (../foo and bare foo)
    text = re.sub(
        r'(href|src)="\.\./([^"]+)"',
        lambda m: f'{m.group(1)}="/{m.group(2)}"'
        if not m.group(2).startswith(("http", "//", "tel:", "mailto:"))
        else m.group(0),
        text,
    )
    for asset in (
        "styles.css",
        "anatomy-icons.js",
        "image-slot.js",
        "site.js",
        "doctor-photos.js",
    ):
        text = re.sub(rf'(href|src)="{re.escape(asset)}', rf'\1="/{asset}', text)
    text = re.sub(r'(href|src)="assets/', r'\1="/assets/', text)

    # Default photo prefix
    text = text.replace('prefix || "/assets/photos/"', 'prefix || "/assets/photos/"')

    return text


def canonical_for(rel_path: Path) -> str:
    if rel_path.name == "/":
        parent = rel_path.parent
        if parent == Path("."):
            return f"{SITE}/"
        return f"{SITE}/{parent.as_posix()}/"
    stem = rel_path.stem
    if stem == "index":
        return f"{SITE}/"
    return f"{SITE}/{stem}/"


def inject_canonical(html: str, url: str) -> str:
    tag = f'<link rel="canonical" href="{url}">'
    if 'rel="canonical"' in html:
        html = re.sub(r'<link rel="canonical" href="[^"]*">', tag, html)
        return html
    if "<head>" in html:
        return html.replace("<head>", f"<head>\n{tag}", 1)
    return html


def process_file(path: Path, rel: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = transform_content(text)
    if path.suffix == ".html":
        text = inject_canonical(text, canonical_for(rel))
    path.write_text(text, encoding="utf-8")


def move_to_index(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "/"
    text = src.read_text(encoding="utf-8")
    text = transform_content(text)
    rel = dest.relative_to(ROOT)
    text = inject_canonical(text, canonical_for(rel))
    dest.write_text(text, encoding="utf-8")
    src.unlink()
    return dest


def main() -> None:
    moved_doctors = 0
    for src in sorted(ROOT.glob("medici/*.html")):
        slug = src.stem
        move_to_index(src, ROOT / "medici" / slug)
        moved_doctors += 1
        print(f"  medici/{slug}.html -> medici/{slug}//")

    for page in ROOT_PAGES:
        src = ROOT / f"{page}.html"
        if src.exists():
            move_to_index(src, ROOT / page)
            print(f"  {page}.html -> {page}//")

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        if path.parts[0] == "scripts" and path.name == "migrate-clean-urls.py":
            continue
        rel = path.relative_to(ROOT)
        process_file(path, rel)

    # generate-schede.py paths
    gen = ROOT / "scripts" / "generate-schede.py"
    text = gen.read_text(encoding="utf-8")
    text = text.replace('MEDICI_HTML = ROOT / "/medici/"', 'MEDICI_HTML = ROOT / "medici" / "/"')
    text = text.replace(
        'raise SystemExit("medici-data JSON not found in /medici/")',
        'raise SystemExit("medici-data JSON not found in /medici/index/")',
    )
    text = text.replace('href="/"', 'href="/"')
    text = text.replace('href="/#aree"', 'href="/#aree"')
    text = text.replace('href="/#struttura"', 'href="/#struttura"')
    text = text.replace('href="/medici/"', 'href="/medici/"')
    text = text.replace('href="/medicina-estetica/"', 'href="/medicina-estetica/"')
    text = text.replace('href="/styles.css', 'href="/styles.css')
    text = text.replace('src="/assets/', 'src="/assets/')
    text = text.replace('src="/anatomy-icons.js', 'src="/anatomy-icons.js')
    text = text.replace('src="/image-slot.js', 'src="/image-slot.js')
    text = text.replace('src="/site.js', 'src="/site.js')
    text = text.replace(
        'return \' src="/assets/photos/usai.webp"\'',
        'return \' src="/assets/photos/usai.webp"\'',
    )
    text = text.replace('out = OUT_DIR / f"{slug}.html"', 'out = OUT_DIR / slug / "/"')
    old_main = """    for doc in medici:
        slug = slugify(doc["surname"])
        out = OUT_DIR / slug / "/"
        if slug == "usai":
            continue  # hand-crafted model page
        out.write_text(render_page(doc), encoding="utf-8")"""
    new_main = """    for doc in medici:
        slug = slugify(doc["surname"])
        out_dir = OUT_DIR / slug
        out = out_dir / "/"
        if slug == "usai":
            continue  # hand-crafted model page
        out_dir.mkdir(parents=True, exist_ok=True)
        out.write_text(render_page(doc), encoding="utf-8")"""
    text = text.replace(old_main, new_main)
    gen.write_text(text, encoding="utf-8")

    print(f"\nDone: {moved_doctors} doctor pages + {len(ROOT_PAGES)} section pages migrated.")


if __name__ == "__main__":
    main()
