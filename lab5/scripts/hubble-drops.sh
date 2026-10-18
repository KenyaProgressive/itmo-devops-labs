#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

if ! hubble status >/dev/null 2>&1; then
  echo "Hubble unavailable"
  exit 1
fi

PGIP=$(kubectl get pod -l 'cnpg.io/cluster=postgres' --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].status.podIP}' 2>/dev/null || true)

kubectl exec deploy/api -- python -c \
  "import socket; socket.create_connection(('postgres-rw',5432),2)" >/dev/null 2>&1 || true
kubectl exec deploy/worker -- python -c \
  "import socket; socket.create_connection(('postgres-rw',5432),2)" >/dev/null 2>&1 || true
if [[ -n "${PGIP:-}" ]]; then
  kubectl exec deploy/api -- python -c \
    "import socket; socket.create_connection(('$PGIP',5432),3)" >/dev/null 2>&1 || true
fi
kubectl exec deploy/api -- python -c \
  "import socket; socket.getaddrinfo('postgres-rw',5432)" >/dev/null 2>&1 || true

sleep 1

echo "=== DROPPED api/worker -> :5432 ==="
hubble observe --last 30 --namespace default --verdict DROPPED --to-port 5432 -o compact 2>/dev/null \
  | grep -E 'api-|worker-' || echo "(нет)"

echo
echo "=== DROPPED -> DNS :53 ==="
hubble observe --last 30 --namespace default --verdict DROPPED --to-port 53 -o compact 2>/dev/null \
  | grep -E 'api-|worker-' || echo "(нет)"
