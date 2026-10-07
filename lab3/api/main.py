import sys
import uvicorn
from contextlib import asynccontextmanager
from http import HTTPStatus
from uuid import UUID

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from config import HEALTH_FAIL, LOG_FORMAT
from db.session import DBMaster
from dependencies import OrderServiceDep
from dto.orders import OrderCreateDTO, OrdersListFilterDTO
from prometheus_fastapi_instrumentator import Instrumentator

logger.remove()

logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    backtrace=True,
    diagnose=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await DBMaster.create_tables()
    yield


app: FastAPI = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health() -> JSONResponse:

    if HEALTH_FAIL:

        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="HEALTH_FAIL=True"
        )

    return JSONResponse(content={"status": "ok"}, status_code=HTTPStatus.OK)


@app.post("/order", status_code=HTTPStatus.CREATED)
async def make_order(order: OrderCreateDTO, service: OrderServiceDep) -> JSONResponse:

    try:
        order_id: UUID = await service.make_order(order=order)
        return JSONResponse(
            content={"order_id": order_id}, status_code=HTTPStatus.CREATED
        )

    except Exception as e:
        logger.exception(f"Making order failed")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Что-то пошло не так. Попробуйте ещё раз.",
        )


@app.get("/orders")
async def list_orders(
    service: OrderServiceDep, filters: OrdersListFilterDTO
) -> JSONResponse:
    try:
        return await service.get_orders(filters=filters)
    except Exception as e:
        logger.exception(f"Getting orders failed")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Что-то пошло не так. Попробуйте ещё раз.",
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)