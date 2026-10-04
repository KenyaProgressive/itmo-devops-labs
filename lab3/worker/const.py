import os
from random import randint

import faker_commerce
from dotenv import load_dotenv
from faker import Faker

load_dotenv(".env")

POSTGRES_URL = f"{os.getenv("POSTGRES_DRIVER")}://{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}@{os.getenv("POSTGRES_HOST")}:{os.getenv("POSTGRES_PORT")}/{os.getenv("POSTGRES_DB")}"


FAKER = Faker(locale="ru_RU")
FAKER.add_provider(faker_commerce.Provider)

SKUS = [randint(1_000_000, 9_999_999) for _ in (100)]
PRODUCTS_NAMES = [FAKER.ecommerce_name() for _ in (100)]
