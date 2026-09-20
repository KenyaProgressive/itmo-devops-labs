#!/usr/bin/env bash

set -euo pipefail

HOST_IF="veth-host" # первый конец пары (хост)
NS_IF="veth-ns" # второй конец пары (ns)

HOST_IP="10.1.1.1/24"
NS_IP="10.1.1.2/24"
NS_ADDR="${NS_IP%/*}"

export NS_IP

sudo -v
sudo ip link del "$HOST_IF" 2>/dev/null || true


# создадим ns
unshare --user --pid --mount --net --uts --ipc --fork --map-root-user --mount-proc \
    bash -c '
        set -e

        hostname l1-cont

        # ожидаем интерфейс veth-ns
        while ! ip link show veth-ns >/dev/null 2>&1; do
            sleep 0.1
        done

        # настройка сети внутри ns
        ip addr add "$NS_IP" dev veth-ns
        ip link set veth-ns up
        ip link set lo up

        # подменяем bash на uvicorn
        exec .venv/bin/uvicorn api.main:app \
            --host 0.0.0.0 \
            --port 8000
    ' &

UNSHARE_PID=$!


# находим хостовый pid запущенного bash
while true; do
    NS_PID=$(pgrep -P "$UNSHARE_PID" | head -n 1 || true)
    if [[ -n "$NS_PID" ]]; then
        break
    fi
    sleep 0.1
done

echo "PID процесса на хосте: $NS_PID"

# настройка veth-пары
sudo ip link add "$HOST_IF" type veth peer name "$NS_IF"

# прокидываем внутрь ns
sudo ip link set "$NS_IF" netns "$NS_PID"

# сетап хостового интерфейса
sudo ip addr add "$HOST_IP" dev "$HOST_IF"
sudo ip link set "$HOST_IF" up

echo "Сервис по адресу: http://${NS_ADDR}:8000"

cleanup() {
    trap - INT TERM EXIT

    echo
    echo "Остановка"

    if kill -0 "$UNSHARE_PID" 2>/dev/null; then
        kill -INT "$UNSHARE_PID" 2>/dev/null || true
        wait "$UNSHARE_PID" 2>/dev/null || true
    fi

    sudo ip link del "$HOST_IF" 2>/dev/null || true

    echo "Остановлено"
}

trap cleanup INT TERM EXIT

wait "$UNSHARE_PID"
