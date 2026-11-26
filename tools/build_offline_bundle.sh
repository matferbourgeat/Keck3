#!/usr/bin/env bash
# Fabrique le paquet d'installation hors ligne de Keck3 pour le PC Windows du banc,
# dont le pare-feu bloque python.org, GitHub et PyPI : Python embarqué + dépendances
# déjà installées, rien n'est téléchargé sur le poste.
#   tools/build_offline_bundle.sh            → dist/Keck3-hors-ligne-<date>.zip
set -euo pipefail

PY_VERSION=3.12.10            # dernière 3.12 publiée en binaire (pywin32 306 a ses wheels cp312)
PY_TAG=312
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
CACHE="$DIST/cache"
NAME="Keck3-hors-ligne-$(date +%Y-%m-%d)"
OUT="$DIST/$NAME"
PIP="$ROOT/venv/bin/pip"

[ -x "$PIP" ] || { echo "venv absent : lancer ./start_keck3.sh une fois"; exit 1; }
git -C "$ROOT" diff --quiet HEAD -- . ':!dist' || echo "⚠ modifications non commitées : le paquet prend HEAD"

rm -rf "$OUT" "$OUT.zip"
mkdir -p "$CACHE" "$OUT"

# 1. Code (version commitée, sans .git : la mise à jour par GitHub se coupe d'elle-même)
git -C "$ROOT" archive --format=tar HEAD | tar -x -C "$OUT"
rm -rf "$OUT/tools" "$OUT/start_keck3.sh" "$OUT/start_web_ui.sh" "$OUT/quick_test"

# 2. Python embarqué pour Windows 64 bits
EMBED="$CACHE/python-$PY_VERSION-embed-amd64.zip"
[ -f "$EMBED" ] || curl -fsSL -o "$EMBED" "https://www.python.org/ftp/python/$PY_VERSION/python-$PY_VERSION-embed-amd64.zip"
mkdir -p "$OUT/python"
unzip -q "$EMBED" -d "$OUT/python"

# Le mode ._pth ignore le dossier du script et les .pth : on liste tout explicitement.
cat > "$OUT/python/python$PY_TAG._pth" <<PTH
python$PY_TAG.zip
.
Lib\\site-packages
Lib\\site-packages\\win32
Lib\\site-packages\\win32\\lib
Lib\\site-packages\\Pythonwin
..
import site
PTH

# 3. Dépendances, wheels Windows. Marqueurs retirés : pip les évaluerait sur le Mac
#    (pywin32, tzdata et colorama de click seraient sautés).
REQ="$CACHE/requirements-win.txt"
sed -E 's/;.*$//' "$ROOT/requirements.txt" | grep -vE '^\s*(#|$)' > "$REQ"
echo "colorama" >> "$REQ"
"$PIP" install --quiet --no-compile --target "$OUT/python/Lib/site-packages" \
  --platform win_amd64 --python-version "$PY_TAG" --implementation cp --only-binary=:all: \
  -r "$REQ"
# DLL de pywin32 à côté de python.exe : chargées sans dépendre de pywin32_bootstrap
cp "$OUT"/python/Lib/site-packages/pywin32_system32/*.dll "$OUT/python/"

# 4. Configuration de test (la clé API est transmise à part, jamais dans le paquet)
mkdir -p "$OUT/data" "$OUT/logs"
cp "$OUT/openprod_mapping.example.json" "$OUT/data/openprod_mapping.json"
cp "$OUT/programs.example.json" "$OUT/data/programs.json"
sed -e 's/^OPEN_PROD_DB=.*/OPEN_PROD_DB=qhse_test/' "$OUT/.env.example" > "$OUT/.env"

# 5. Lanceurs (CRLF pour cmd.exe)
crlf() { sed 's/$/\r/' > "$1"; }
crlf "$OUT/Keck3.cmd" <<'CMD'
@echo off
cd /d "%~dp0"
echo Keck3 demarre. Ouvrir http://127.0.0.1:5000 dans le navigateur.
python\python.exe web_ui.py
pause
CMD
crlf "$OUT/Diagnostic.cmd" <<'CMD'
@echo off
cd /d "%~dp0"
python\python.exe test_setup.py
pause
CMD
crlf "$OUT/Test_imprimantes.cmd" <<'CMD'
@echo off
cd /d "%~dp0"
echo Imprimantes vues par ce poste :
python\python.exe printer_test.py
echo.
set /p GO=Imprimer les deux etiquettes de test F1-1 ? (o/n) 
if /i "%GO%"=="o" (
  python\python.exe printer_test.py barcode F1-1
  python\python.exe printer_test.py serial F1-1
)
pause
CMD
rm -f "$OUT/start_keck3.cmd" "$OUT/start_web_ui.cmd"

crlf "$OUT/LISEZMOI.txt" <<TXT
Keck3 - installation hors ligne (banc de controle D1118)
Paquet du $(date +%d/%m/%Y), commit $(git -C "$ROOT" rev-parse --short HEAD), Python $PY_VERSION embarque.

Rien a installer ni a telecharger : tout est dans ce dossier.

1. Copier le dossier entier dans C:\\Keck3 (chemin sans espace).
2. Ouvrir .env avec le Bloc-notes, remplacer your_id_secret_here par la cle API
   Open Prod transmise a part, enregistrer.
3. Double-cliquer Diagnostic.cmd : tout doit etre en coche, en particulier
   "Open Prod". Si "Serveur injoignable" : le poste n'a pas acces a misrv-opp1
   en HTTPS, demande a faire au support informatique.
   Si le port serie n'est pas trouve : mettre SERIAL_PORT=COM3 (ou le port
   indique) dans .env.
4. Double-cliquer Test_imprimantes.cmd : verifier que les deux SATO
   \\\\misrv-imp\\MI-IMPCB-M1-01 et -02 apparaissent, puis imprimer le test.
5. Double-cliquer Keck3.cmd, ouvrir http://127.0.0.1:5000, lancer un controle
   sur le banc.

A renvoyer : logs\\keck3.log et les numeros de programme utilises sur le banc.
TXT

# 6. Archive
(cd "$DIST" && rm -f "$NAME.zip" && zip -qr "$NAME.zip" "$NAME")
echo "$DIST/$NAME.zip ($(du -h "$DIST/$NAME.zip" | cut -f1))"
