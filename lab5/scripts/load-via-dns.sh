#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
DURATION="${DURATION:-120}"
SLEEP="${SLEEP:-0.1}"
OUT="${OUT:-lab5/screens/load-chaos.csv}"
MODE="${MODE:-nodeport}"

NODE_IP="${NODE_IP:-$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')}"
NODE_PORT="${NODE_PORT:-30082}"

mkdir -p "$(dirname "$OUT")"
echo "timestamp,result" > "$OUT"

ok=0
fail=0
end=$((SECONDS + DURATION))

if [[ "$MODE" == "dns" ]]; then
  kubectl exec -n "$NAMESPACE" deploy/worker -- sh -c "
    end=\$(( \$(date +%s) + $DURATION ))
    ok=0; fail=0
    while [ \$(date +%s) -lt \$end ]; do
      if wget -qO- --timeout=2 http://api:8000/health >/dev/null 2>&1; then
        ok=\$((ok+1)); echo ok
      else
        fail=\$((fail+1)); echo fail
      fi
      sleep $SLEEP
    done
    echo SUMMARY ok=\$ok fail=\$fail >&2
  " 2> >(tee /tmp/load-dns-summary >&2) | while read -r line; do
    ts=$(date -Is)
    if [[ "$line" == "ok" ]]; then
      echo "${ts},ok" >> "$OUT"
      ok=$((ok + 1))
    elif [[ "$line" == "fail" ]]; then
      echo "${ts},fail" >> "$OUT"
      fail=$((fail + 1))
    fi
    printf "\r ok=%s fail=%s" "$ok" "$fail"
  done
  echo
else
  while (( SECONDS < end )); do
    ts=$(date -Is)
    if curl -sS -m 2 "http://${NODE_IP}:${NODE_PORT}/health" >/dev/null 2>&1; then
      echo "${ts},ok" >> "$OUT"
      ok=$((ok + 1))
    else
      echo "${ts},fail" >> "$OUT"
      fail=$((fail + 1))
    fi
    printf "\r ok=%s fail=%s" "$ok" "$fail"
    sleep "$SLEEP"
  done
  echo
fi

echo "DONE ok=$ok fail=$fail total=$((ok + fail)) mode=$MODE"
echo "CSV: $OUT"
if (( fail == 0 )); then
  echo "PASS: zero failed requests"
else
  echo "FAIL: had failed requests"
  exit 1
fi
