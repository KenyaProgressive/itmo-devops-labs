import asyncio
import sys
from random import randint
from types import OrderCreateTuple, ProductCreateTuple

import asyncpg
from loguru import logger

from const import FAKER, POSTGRES_URL, PRODUCTS_NAMES, SKUS

# Настройка логирования
logger.remove()
logger.add(
    sys.stderr,
    backtrace=True,
    diagnose=False,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
)

products_data: list[ProductCreateTuple] = [
    ProductCreateTuple(name=PRODUCTS_NAMES[i], sku=SKUS[i]) for i in range(100)
]

orders_data: list[OrderCreateTuple] = [
    OrderCreateTuple(
        phone_number=FAKER.phone_number(),
        customer_name=FAKER.name(),
        sku=sku_num,
        quantity=randint(1, 100),
    )
    for sku_num in SKUS
]


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
                    await asyncio.sleep(3)
                    continue

                processed_ids = []
                for row in rows:
                    logger.info(
                        f"Processing order #{row['id']} ({row['name']} x {row['quantity']})..."
                    )
                    await asyncio.sleep(1)  # Имитация работы
                    processed_ids.append(row["id"])

                if processed_ids:

                    await conn.execute(
                        "UPDATE orders SET is_processed = TRUE WHERE id = ANY($1::uuid[])",
                        processed_ids,
                    )
                    logger.info(f"Orders {processed_ids} marked as PROCESSED")

        except Exception:
            logger.exception("Worker loop error")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(processing_orders())
