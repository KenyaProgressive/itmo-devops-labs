import asyncio
import sys
from random import randint
from worker_types import OrderCreateTuple, ProductCreateTuple
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from const import ORDERS_PROCESSED, WORKER_ERRORS
import asyncpg
from loguru import logger
from aiohttp import web

from const import FAKER, POSTGRES_URL, PRODUCTS_NAMES, SKUS, MAX_RECORDS

# Настройка логирования
logger.remove()
logger.add(
    sys.stderr,
    backtrace=True,
    diagnose=False,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
)

products_data: list[ProductCreateTuple] = [
    ProductCreateTuple(name=PRODUCTS_NAMES[i], sku=str(SKUS[i])) for i in range(100)
]

orders_data: list[OrderCreateTuple] = [
    OrderCreateTuple(
        phone_number=FAKER.phone_number(),
        customer_name=FAKER.name(),
        sku=str(sku_num),
        quantity=randint(1, 100),
    )
    for sku_num in SKUS
]

async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="ok")

async def metrics_handler(request: web.Request) -> web.Response:
    return web.Response(
        body=generate_latest(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )

async def run_health_server() -> None:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8081)
    await site.start()

    logger.info(f"Health server listening on :{8081}")

    await asyncio.Event().wait()



async def init_test_data(pool):
    """Функция для безопасной вставки тестовых данных"""
    logger.info("Inserting test data...")
    async with pool.acquire() as conn:

        await conn.executemany(
            "INSERT INTO products(name, sku) VALUES($1, $2) ON CONFLICT (sku) DO NOTHING",
            [(p.name, p.sku) for p in products_data],
        )

        await conn.executemany(
            "INSERT INTO orders(phone_number, customer_name, sku, quantity) VALUES($1, $2, $3, $4)",
            [(o.phone_number, o.customer_name, o.sku, o.quantity) for o in orders_data],
        )

    logger.info("Test data ready.")


async def processing_orders():

    logger.info("Worker started.")
    counter: int = 0

    pool = await asyncpg.create_pool(dsn=POSTGRES_URL, min_size=1, max_size=10)

    # Наполняем базу один раз при старте
    await init_test_data(pool)

    while True:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT orders.id, products.name, orders.quantity 
                    FROM orders 
                    JOIN products ON orders.sku = products.sku 
                    WHERE orders.is_processed = FALSE 
                    LIMIT 10
                    """)

                if not rows:
                    await asyncio.sleep(10)
                    continue

                processed_ids = []
                for row in rows:
                    logger.info(
                        f"Processing order #{row['id']} ({row['name']} x {row['quantity']})..."
                    )
                    await asyncio.sleep(5)  # Имитация работы
                    processed_ids.append(row["id"])

                if processed_ids:

                    await conn.execute(
                        "UPDATE orders SET is_processed = TRUE WHERE id = ANY($1::uuid[])",
                        processed_ids,
                    )
                    logger.info(f"Orders {processed_ids} marked as PROCESSED")

                    counter += len(processed_ids)
                    ORDERS_PROCESSED.inc(len(processed_ids))
                
                if counter > MAX_RECORDS:
                    await conn.execute("TRUNCATE TABLE orders")
                    await conn.execute("TRUNCATE TABLE products")
                    counter = 0
                    

        except Exception:
            logger.exception("Worker loop error")
            WORKER_ERRORS.inc()
            await asyncio.sleep(5)


async def main() -> None:
    await asyncio.gather(
        processing_orders(),
        run_health_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
