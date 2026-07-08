#!/usr/bin/env bash
# Converte un ritratto medico JPG/PNG in WebP ottimizzato (max 1200px, q=82).
# Uso: ./scripts/convert-portrait.sh assets/photos/nome.jpg
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CWEBP="${CWEBP:-$(command -v cwebp || echo /usr/local/bin/cwebp)}"

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <file.jpg|file.png> [output.webp]" >&2
  exit 1
fi

src="$1"
if [[ "$src" != /* ]]; then src="$ROOT/$src"; fi
[[ -f "$src" ]] || { echo "File non trovato: $src" >&2; exit 1; }

base="$(basename "${src%.*}")"
dir="$(dirname "$src")"
out="${2:-$dir/${base}.webp}"
if [[ "$out" != /* ]]; then out="$ROOT/$out"; fi

tmp="$(mktemp "/tmp/ms_${base}.XXXXXX.jpg")"
trap 'rm -f "$tmp"' EXIT

sips -Z 1200 "$src" --out "$tmp" >/dev/null
"$CWEBP" -q 82 -m 6 -mt "$tmp" -o "$out"

orig=$(stat -f%z "$src")
new=$(stat -f%z "$out")
echo "OK: $(basename "$src") -> $(basename "$out")  (${orig} -> ${new} bytes)"
