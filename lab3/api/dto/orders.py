from typing import Annotated
from uuid import UUID

from pydantic import Field

from dto.base import DTO


class OrderCreateDTO(DTO):
    phone_number: Annotated[
        str,
        Field(
            max_length=12,
            title="Телефонный номер заказчика",
            description="12 символов -- + и 11 цифр",
        ),
    ]
    customer_name: Annotated[str, Field(max_length=150, title="Имя заказчика")]
    sku: Annotated[
        str,
        Field(
            max_length=7,
            title="Артикул заказа",
            description="7-значный номер товара в системе",
        ),
    ]
    quantity: Annotated[
        int,
        Field(
            default=1,
            gt=0,
            le=100,
            title="Количество заказанных единиц",
            description="Количество заказанных единиц товара (от 1 до 100)",
        ),
    ]


class OrderDTO(DTO):
    id: UUID
    phone_number: Annotated[
        str,
        Field(
            max_length=12,
            title="Телефонный номер заказчика",
            description="12 символов -- + и 11 цифр",
        ),
    ]
    product_name: Annotated[
        str,
        Field(
            max_length=200,
            title="Название товара",
            description="Название товара в системе",
        ),
    ]
    quantity: Annotated[
        int,
        Field(
            default=1,
            gt=0,
            le=100,
            title="Количество заказанных единиц",
            description="Количество заказанных единиц товара (от 1 до 100)",
        ),
    ]
    sku: Annotated[
        str,
        Field(
            max_length=7,
            title="Артикул заказа",
            description="7-значный номер товара в системе",
        ),
    ]


class OrdersListFilterDTO(DTO):
    order_id: UUID | None = None
    phone_number: str | None = None
    quantity: int | None = None
    sku: str | None = None
