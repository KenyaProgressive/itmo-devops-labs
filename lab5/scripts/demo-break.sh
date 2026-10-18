#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VARIANT="${1:?usage: $0 wrong-port|wrong-label|no-dns|no-clients}"

export PATH="$HOME/.local/bin:$PATH"

if ! hubble status >/dev/null 2>&1; then
  echo "Hubble unavailable"
  exit 1
fi

"$ROOT/scripts/break-network.sh" "$VARIANT"
"$ROOT/scripts/check-matrix.sh" || true
"$ROOT/scripts/hubble-drops.sh"
