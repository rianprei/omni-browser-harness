#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v python3 >/dev/null; then echo 'Python 3.10+ necessário' >&2; exit 1; fi
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
if ! command -v chromium >/dev/null && ! command -v chromium-browser >/dev/null && ! command -v google-chrome >/dev/null; then
  python -m playwright install chromium
fi
printf '\nInstalado. Execute:\n  source .venv/bin/activate\n  omni-browser login\n  omni-browser github-create --owner rianprei --name omni-research-oss --public --apply\n'
