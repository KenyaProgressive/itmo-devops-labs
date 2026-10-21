#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHART="$ROOT/k8s/shop-chart"

helm upgrade shop "$CHART" -n default -f "$CHART/values.yaml"
rm -f "$ROOT/screens/.break-overlay.yaml" "$ROOT/screens/.break-id"
"$ROOT/scripts/check-matrix.sh"
