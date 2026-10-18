#!/usr/bin/env bash
set -euo pipefail

NS="${NAMESPACE:-default}"

tcp_python() {
  local ref="$1" host="$2" port="$3"
  kubectl exec -n "$NS" "$ref" -- python -c \
    "import socket; s=socket.create_connection(('${host}', ${port}), 3); s.close(); print('ok')" \
    2>/dev/null || echo "blocked"
}

tcp_wget() {
  local ref="$1" host="$2" port="$3"
  local out
  out=$(kubectl exec -n "$NS" "$ref" -- \
    sh -c "wget -T 3 -O /dev/null http://${host}:${port} 2>&1" 2>/dev/null || true)
  if echo "$out" | grep -qiE 'timed out|can.t connect|network is unreachable|no route'; then
    echo "blocked"
  else
    echo "ok"
  fi
}

dns_ok() {
  kubectl exec -n "$NS" deploy/api -- python -c \
    "import socket; print(socket.getaddrinfo('postgres-rw', 5432)[0][4][0])" \
    >/dev/null 2>&1 && echo ok || echo blocked
}

echo "=== матрица (фактически) ==="
echo

api_pg=$(tcp_python deploy/api postgres-rw 5432)
worker_pg=$(tcp_python deploy/worker postgres-rw 5432)
stranger_pg=$(tcp_wget pod/stranger postgres-rw 5432)
stranger_api=$(tcp_wget pod/stranger api 8000)
api_dns=$(dns_ok)

host_api="ok"
if ! curl -sS -m 3 "http://$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'):30082/health" | grep -q ok; then
  host_api="blocked"
fi

printf "%-14s -> %-10s  expected=%-8s  actual=%s\n" "host/NodePort" "api" "ok" "$host_api"
printf "%-14s -> %-10s  expected=%-8s  actual=%s\n" "api" "postgres" "ok" "$api_pg"
printf "%-14s -> %-10s  expected=%-8s  actual=%s\n" "worker" "postgres" "ok" "$worker_pg"
printf "%-14s -> %-10s  expected=%-8s  actual=%s\n" "stranger" "postgres" "blocked" "$stranger_pg"
printf "%-14s -> %-10s  expected=%-8s  actual=%s\n" "stranger" "api" "blocked" "$stranger_api"
printf "%-14s -> %-10s  expected=%-8s  actual=%s\n" "api" "DNS" "ok" "$api_dns"
echo

fail=0
[[ "$host_api" == ok ]] || fail=1
[[ "$api_pg" == ok ]] || fail=1
[[ "$worker_pg" == ok ]] || fail=1
[[ "$stranger_pg" == blocked ]] || fail=1
[[ "$stranger_api" == blocked ]] || fail=1
[[ "$api_dns" == ok ]] || fail=1

if (( fail == 0 )); then
  echo "окей"
else
  echo "не окей"
  exit 1
fi
