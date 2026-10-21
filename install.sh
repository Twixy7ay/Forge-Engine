#!/usr/bin/env bash
set -Eeuo pipefail

REPO="https://github.com/Twixy7ay/Forge-Engine.git"
BASE="${HOME}/.local/share/forge-engine"
BIN="${HOME}/.local/bin"
SRC="${BASE}/source"
VENV="${BASE}/venv"

say() { printf '\n[Forge Engine] %s\n' "$*"; }
die() { printf '\n[Forge Engine] FEHLER: %s\n' "$*" >&2; exit 1; }

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) die "Nur macOS und Linux werden unterstützt." ;;
esac

command -v python3 >/dev/null || die "Python 3 fehlt."
command -v git >/dev/null || die "Git fehlt."

mkdir -p "$BASE" "$BIN"

if [[ -d "$SRC/.git" ]]; then
  [[ -z "$(git -C "$SRC" status --porcelain)" ]] ||
    die "Lokale Änderungen in $SRC vorhanden. Bitte zuerst sichern."
  git -C "$SRC" pull --ff-only ||
    die "Update nicht möglich. Bestehenden Checkout bitte prüfen."
elif [[ -e "$SRC" ]]; then
  die "$SRC existiert, ist aber kein Git-Repository."
else
  git clone --branch main --depth 1 "$REPO" "$SRC" ||
    die "Klonen fehlgeschlagen. Prüfe Internetzugang und GitHub-Zugriff."
fi

[[ -f "$SRC/pyproject.toml" ]] || die "pyproject.toml fehlt."
[[ -d "$SRC/forge_engine" ]] || die "Python-Paket forge_engine fehlt."

if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV" ||
    die "Virtuelle Umgebung fehlgeschlagen. Auf Ubuntu eventuell python3-venv installieren."
fi

"$VENV/bin/python" -m pip install -e "$SRC"

cat > "$BIN/forge" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/forge" "\$@"
EOF
chmod 755 "$BIN/forge"

cat > "$BIN/forge-menu" <<'MENU'
#!/usr/bin/env bash
set -u
FORGE="${HOME}/.local/bin/forge"

pause() { printf '\nEnter drücken, um fortzufahren...'; read -r _; }

while true; do
  clear 2>/dev/null || true
  printf '%s\n' '================================' \
    '          Forge Engine' \
    '================================' \
    '1) Hilfe anzeigen' \
    '2) Version anzeigen' \
    '3) Container auflisten' \
    '4) Konfigurationsprüfung aufrufen' \
    '0) Beenden'
  printf '\nAuswahl: '
  read -r choice || exit 0

  case "$choice" in
    1) "$FORGE" --help; pause ;;
    2) "$FORGE" --version; pause ;;
    3) "$FORGE" ps; pause ;;
    4) "$FORGE" config validate; pause ;;
    0) exit 0 ;;
    *) echo "Ungültige Auswahl."; pause ;;
  esac
done
MENU
chmod 755 "$BIN/forge-menu"

say "Installation abgeschlossen."
say "CLI: $BIN/forge"
say "Menü: $BIN/forge-menu"
say "Es wurden keine bestehenden Container oder Volumes verändert."
exec "$BIN/forge-menu"
