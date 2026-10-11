import time, socket
from multiprocessing import Process
from const import CPU_WORKERS, GROW_STEP_MB, MEM_MB, GROW_INTERVAL_S, LOG_INTERVAL_S

HOST = socket.gethostname()

def cpu_hog():
    x = 1
    while True:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF

def main():

    for _ in range(CPU_WORKERS):
        Process(target=cpu_hog, daemon=True).start()

    chunks = []
    step = GROW_STEP_MB * 1024 * 1024
    target_chunks = MEM_MB // GROW_STEP_MB

    while True:
        if len(chunks) < target_chunks:
            chunks.append(bytearray(step))
            print(f"[{HOST}] mem={len(chunks) * GROW_STEP_MB}MB growing", flush=True)
            time.sleep(GROW_INTERVAL_S)
        else:
            print(f"[{HOST}] mem={len(chunks) * GROW_STEP_MB}MB steady cpu_workers={CPU_WORKERS}", flush=True)
            time.sleep(LOG_INTERVAL_S)

if __name__ == "__main__":
    main()