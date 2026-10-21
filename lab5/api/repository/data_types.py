from typing import TypedDict
from uuid import UUID


class OrderCreate(TypedDict):
    phone_number: str
    customer_name: str
    sku: str
    quantity: int


class OrdersData(TypedDict):
    id: UUID
    phone_number: str
    product_name: str
    sku: str
    quantity: int
