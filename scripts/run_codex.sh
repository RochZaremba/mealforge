#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if ! command -v codex >/dev/null 2>&1; then
  echo 'Brak polecenia codex. Zainstaluj/zaloguj Codex CLI albo otwórz repo w IDE i wklej PROMPT_START.txt.' >&2
  exit 127
fi
python3 scripts/validate_kit.py
exec codex "$(cat PROMPT_START.txt)"
