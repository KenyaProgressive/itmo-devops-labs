import os

MEM_MB          = int(os.environ.get("MEM_MB", "256"))
CPU_WORKERS     = int(os.environ.get("CPU_WORKERS", "2"))
GROW_STEP_MB    = int(os.environ.get("GROW_STEP_MB", "16"))
GROW_INTERVAL_S = float(os.environ.get("GROW_INTERVAL_S", "2"))
LOG_INTERVAL_S  = float(os.environ.get("LOG_INTERVAL_S", "5"))