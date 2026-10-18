#!/bin/sh
# macOS: dê duplo clique. Linux: ./Abrir-Painel.command
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then exec python3 scripts/sac.py painel; else exec python scripts/sac.py painel; fi
