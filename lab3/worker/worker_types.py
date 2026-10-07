from typing import NamedTuple


class OrderCreateTuple(NamedTuple):
    phone_number: str
    customer_name: str
    sku: str
    quantity: int


class ProductCreateTuple(NamedTuple):
    name: str
    sku: str
