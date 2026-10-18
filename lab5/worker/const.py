import os
from random import randint

import faker_commerce
from dotenv import load_dotenv
from faker import Faker
from prometheus_client import Counter

load_dotenv(".env")

POSTGRES_URL = f"{os.getenv("POSTGRES_DRIVER")}://{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}@{os.getenv("POSTGRES_HOST")}:{os.getenv("POSTGRES_PORT")}/{os.getenv("POSTGRES_DB")}"


FAKER = Faker(locale="ru_RU")
FAKER.add_provider(faker_commerce.Provider)

SKUS = [randint(1_000_000, 9_999_999) for _ in range(100)]
PRODUCTS_NAMES = [FAKER.ecommerce_name() for _ in range(100)]
MAX_RECORDS = 10000

ORDERS_PROCESSED = Counter(
    "worker_orders_processed_total",
    "Total number of orders processed",
)

WORKER_ERRORS = Counter(
    "worker_errors_total",
    "Total number of worker errors",
)



