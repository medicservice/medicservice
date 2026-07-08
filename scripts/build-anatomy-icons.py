#!/usr/bin/env python3
"""Genera anatomy-icons.js dalle Health Icons (CC0) — outline 48px, spessore uniforme."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS_ROOT = ROOT / "package" / "public" / "icons" / "svg"
OUT = ROOT / "anatomy-icons.js"
TARGET_VB = "0 0 48 48"

# Percorsi outline 48px; organi/anatomia preferiti alle badge "specialty" (cornice più spessa)
ICON_PATHS: dict[str, list[str]] = {
    "heart_organ": ["outline/body/heart_organ.svg"],
    "lungs": ["outline/body/lungs.svg"],
    "allergies": ["outline/conditions/allergies.svg"],
    "spine": ["outline/body/spine.svg"],
    "stomach": ["outline/body/stomach.svg"],
    "colon": ["outline/body/colon.svg"],
    "kidneys": ["outline/body/kidneys.svg"],
    "andrology": ["outline/symbols/male.svg"],
    "blood_vessel": ["outline/body/blood_vessel.svg"],
    "gynecology": ["outline/body/female_reproductive_system.svg"],
    "breasts": ["outline/body/breasts.svg"],
    "physical_therapy": ["outline/exercise/weights.svg", "outline/specialties/physical_therapy.svg"],
    "nerve": ["outline/body/nerve.svg"],
    "thyroid": ["outline/body/thyroid.svg"],
    "pancreas": ["outline/body/pancreas.svg"],
    "blood_cells": ["outline/body/blood_cells.svg"],
    "lymph_nodes": ["outline/body/lymph_nodes.svg"],
    "oncology": ["outline/body/cell_nuclei.svg", "outline/conditions/cancerous_cell_nuclei.svg"],
    "head": ["outline/body/head.svg"],
    "dermatology": ["outline/conditions/skin_cancer.svg"],
    "mouth": ["outline/body/mouth.svg", "outline/specialties/speech_language_therapy.svg"],
    "neurology": ["outline/body/neurology.svg"],
    "neuro_surgery": ["outline/people/neuro_surgery.svg"],
    "mental_disorders": ["outline/people/mental_disorders.svg"],
    "eye": ["outline/body/eye.svg"],
    "ent": ["outline/body/ear.svg"],
    "orthopaedics": ["outline/body/skeleton.svg", "outline/body/joints.svg"],
    "traumatism": ["outline/people/traumatism.svg"],
    "joints": ["outline/body/joints.svg"],
    "xray": ["outline/devices/xray.svg"],
    "general_surgery": ["outline/body/liver.svg"],
    "geriatrics": ["outline/symbols/cardiogram.svg", "outline/specialties/geriatrics.svg"],
    "nutrition": ["outline/nutrition/nutrition.svg"],
    "pediatrics": ["outline/specialties/pediatrics.svg", "outline/people/boy_0105y.svg"],
    "justice": ["outline/objects/justice.svg"],
    "diabetes": ["outline/people/diabetes.svg", "outline/devices/diabetes_measure.svg"],
    "syringe": ["outline/devices/syringe.svg"],
    "pain": ["outline/conditions/pain.svg", "outline/conditions/back_pain.svg"],
    "endocrinology": ["outline/body/thyroid.svg"],
    "urology": ["outline/body/kidneys.svg", "outline/body/bladder.svg"],
    "rheumatology": ["outline/body/joints.svg"],
    "face": ["outline/body/head.svg"],
}

SPECIALTY_MAP: dict[str, str] = {
    "Allergologia": "allergies",
    "Andrologia": "andrology",
    "Flebologia": "blood_vessel",
    "Cardiologia": "heart_organ",
    "Chirurgia generale": "general_surgery",
    "Chiropratica": "spine",
    "Dermatologia": "dermatology",
    "Dermopigmentazione": "syringe",
    "Diabetologia": "diabetes",
    "Elettromiografia": "nerve",
    "Ematologia": "blood_cells",
    "Endocrinologia": "endocrinology",
    "Fisiatria": "spine",
    "Fisioterapia": "physical_therapy",
    "Gastroenterologia": "stomach",
    "Geriatria": "geriatrics",
    "Ginecologia": "gynecology",
    "Immunologia": "lymph_nodes",
    "Logopedia": "mouth",
    "Medicina estetica": "face",
    "Medicina legale": "justice",
    "Neurochirurgia": "neuro_surgery",
    "Neurologia": "neurology",
    "Nutrizione": "nutrition",
    "Oculistica": "eye",
    "Oncologia": "oncology",
    "Ortopedia": "orthopaedics",
    "Otorinolaringoiatria": "ent",
    "Pedagogia": "pediatrics",
    "Pneumologia": "lungs",
    "Proctologia": "colon",
    "Psichiatria": "mental_disorders",
    "Radiologia": "xray",
    "Reumatologia": "rheumatology",
    "Senologia": "breasts",
    "Terapia del dolore": "pain",
    "Traumatologia": "traumatism",
    "Tricologia": "head",
    "Urologia": "urology",
}


def parse_svg(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    vb = re.search(r'viewBox="([^"]+)"', text)
    viewbox = vb.group(1) if vb else "0 0 48 48"
    inner = re.sub(r"^.*?<svg[^>]*>", "", text, count=1, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S).strip()
    inner = re.sub(r"\s+", " ", inner)
    return viewbox, inner


def normalize_to_48(viewbox: str, inner: str) -> tuple[str, str]:
    """Porta tutte le icone a viewBox 48×48 per spessore visivo coerente."""
    parts = viewbox.strip().split()
    if len(parts) == 4 and parts[2] == "24" and parts[3] == "24":
        inner = f'<g transform="scale(2)">{inner}</g>'
        return TARGET_VB, inner
    return viewbox, inner


def resolve_icon(key: str) -> tuple[str, str, str]:
    for rel in ICON_PATHS[key]:
        path = ICONS_ROOT / rel
        if path.is_file():
            vb, inner = parse_svg(path)
            vb, inner = normalize_to_48(vb, inner)
            return key, vb, inner
    raise FileNotFoundError(f"Nessun file trovato per icona '{key}': {ICON_PATHS[key]}")


def main() -> None:
    if not ICONS_ROOT.is_dir():
        raise SystemExit(
            "Health Icons non trovate. Esegui: npm pack healthicons && tar -xzf healthicons-*.tgz"
        )

    used_keys = sorted(set(SPECIALTY_MAP.values()))
    icons: dict[str, tuple[str, str]] = {}
    for key in used_keys:
        _, vb, inner = resolve_icon(key)
        icons[key] = (vb, inner)

    lines = [
        "/* Icone specialità — Health Icons (CC0) https://healthicons.org",
        "   Outline 48px normalizzato. Generato da scripts/build-anatomy-icons.py */",
        "(function () {",
        "  const ICONS = {",
    ]

    for key in used_keys:
        vb, inner = icons[key]
        lines.append(f"    {key}: {{ vb: {json.dumps(vb)}, m: {json.dumps(inner)} }},")

    lines.append("  };")
    lines.append("")
    lines.append("  const MAP = {")
    for spec in sorted(SPECIALTY_MAP):
        lines.append(f'    {json.dumps(spec, ensure_ascii=False)}: {json.dumps(SPECIALTY_MAP[spec])},')
    lines.append("  };")
    lines.append("")
    lines.append("  window.specIcon = function (name) {")
    lines.append("    const key = MAP[name];")
    lines.append("    const ic = key && ICONS[key];")
    lines.append("    if (ic) {")
    lines.append(
        '      return \'<svg class="health-icon" viewBox="\' + ic.vb + '
        '\'\" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">\' + ic.m + \'</svg>\';'
    )
    lines.append("    }")
    lines.append('    return \'<i data-lucide="stethoscope"></i>\';')
    lines.append("  };")
    lines.append("})();")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    vbs = {vb for vb, _ in icons.values()}
    print(f"Scritto {OUT} — {len(icons)} icone, viewBox: {', '.join(sorted(vbs))}")


if __name__ == "__main__":
    main()
