from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

allocated_memory: list[bytearray] = []


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/eat")
def eat(mb: int) -> dict[str, int]:
    chunk = bytearray(mb * 1024 * 1024)
    allocated_memory.append(chunk)

    return {
        "allocated_mb": mb,
        "total_allocations": len(allocated_memory),
    }


@app.get("/burn")
def burn() -> None:
    while True:
        pass