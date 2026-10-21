#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHART="$ROOT/k8s/shop-chart"
OVERLAY="$ROOT/screens/.break-overlay.yaml"
IDFILE="$ROOT/screens/.break-id"
CHOICE="${1:?usage: $0 wrong-port|wrong-label|no-dns|no-clients}"

mkdir -p "$ROOT/screens"

case "$CHOICE" in
  wrong-label)
    cat > "$OVERLAY" <<'EOF'
networkPolicies:
  postgres:
    podLabels:
      cnpg.io/cluster: broken-cluster-name
EOF
    ;;
  wrong-port)
    cat > "$OVERLAY" <<'EOF'
networkPolicies:
  postgres:
    allowPort: 9999
EOF
    ;;
  no-dns)
    cat > "$OVERLAY" <<'EOF'
networkPolicies:
  dns:
    enabled: false
EOF
    ;;
  no-clients)
    cat > "$OVERLAY" <<'EOF'
networkPolicies:
  postgres:
    clientAppLabels: []
EOF
    ;;
  *)
    echo "unknown variant: $CHOICE"
    exit 1
    ;;
esac

echo "$CHOICE" > "$IDFILE"
helm upgrade shop "$CHART" -n default -f "$CHART/values.yaml" -f "$OVERLAY"
