#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${INTERVAL:-2}"
NAMESPACE="${NAMESPACE:-default}"
READY_COUNT="${READY_COUNT:-3}"

ready_api() {
  kubectl get pods -n "$NAMESPACE" -l app=api --no-headers 2>/dev/null \
    | awk '$2 ~ /^1\/1$/ && $3 == "Running" {c++} END {print c+0}'
}

while true; do
  while (( $(ready_api) < READY_COUNT )); do
    sleep 1
  done

  POD=$(kubectl get pods -n "$NAMESPACE" -l app=api \
    --field-selector=status.phase=Running \
    -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | grep -v '^$' | shuf -n 1 || true)

  if [[ -z "${POD:-}" ]]; then
    sleep "$INTERVAL"
    continue
  fi

  echo "$(date -Is) delete $POD"
  kubectl delete pod -n "$NAMESPACE" "$POD" --wait=false
  sleep "$INTERVAL"
done
