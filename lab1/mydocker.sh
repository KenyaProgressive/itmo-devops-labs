#!/usr/bin/env bash

set -euo pipefail

HOST_IF="veth-host" # первый конец пары (хост)
NS_IF="veth-ns" # второй конец пары (ns)

HOST_IP="10.1.1.1/24"
NS_IP="10.1.1.2/24"
NS_ADDR="${NS_IP%/*}"

CGROUP="/sys/fs/cgroup/lab1"
MEMORY_MAX=$((64 * 1024 * 1024)) # 64 мб
SWAP_MAX=0 # swap запрещен
CPU_MAX="50000 100000" # 0.5 CPU
PIDS_MAX=20

export NS_IP

sudo -v

# чистим старый запуск
sudo ip link del "$HOST_IF" 2>/dev/null || true

if [[ -d "$CGROUP" ]]; then
    echo 1 | sudo tee "$CGROUP/cgroup.kill" >/dev/null 2>&1 || true
    sudo rmdir "$CGROUP" 2>/dev/null || true
fi

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

        # запускаем uvicorn уже без capabilities
        exec capsh --drop=all --caps= --noamb -- -c "
            exec /usr/bin/python3 seccomp_runner.py \
                .venv/bin/uvicorn api.main:app \
                --host 0.0.0.0 \
                --port 8000
        "
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

# cgroups
sudo mkdir "$CGROUP"

echo "$NS_PID" | sudo tee "$CGROUP/cgroup.procs" >/dev/null

# память ограничиваем
echo "$MEMORY_MAX" | sudo tee "$CGROUP/memory.max" >/dev/null
echo "$SWAP_MAX"   | sudo tee "$CGROUP/memory.swap.max" >/dev/null

# cpu ограничиваем
echo "$CPU_MAX" | sudo tee "$CGROUP/cpu.max" >/dev/null

# процессы ограничиваем
echo "$PIDS_MAX" | sudo tee "$CGROUP/pids.max" >/dev/null

echo "Cgroup: $CGROUP"
echo "Memory: $MEMORY_MAX bytes"
echo "CPU: $CPU_MAX"
echo "PIDs: $PIDS_MAX"

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

    # очистка cgroups после остановки (закомментить если нужно посмотреть всякие ивенты, оом и тд)
    if [[ -d "$CGROUP" ]]; then
        echo 1 | sudo tee "$CGROUP/cgroup.kill" >/dev/null 2>&1 || true
        sudo rmdir "$CGROUP" 2>/dev/null || true
    fi

    echo "Остановлено"
}

trap cleanup INT TERM EXIT

wait "$UNSHARE_PID"
