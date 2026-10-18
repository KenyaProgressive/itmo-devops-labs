from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Orders, Products
from repository.data_types import OrderCreate, OrdersData


class OrdersRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_order_data(self, order: OrderCreate) -> UUID:
        query = (
            insert(Orders)
            .values(
                phone_number=order["phone_number"],
                customer_name=order["customer_name"],
                sku=order["sku"],
                quantity=order["quantity"],
            )
            .returning(Orders.id)
        )

        res = await self._session.execute(query)
        return res.scalar_one()

    async def get_orders_data(
        self,
        order_id: UUID | None = None,
        phone_number: str | None = None,
        sku: str | None = None,
        quantity: int | None = None,
    ) -> list[OrdersData]:
        query = select(Orders.id, Orders.phone_number, Products.name, Orders.quantity, Orders.sku).join(Products, Orders.sku == Products.sku)

        if order_id is not None:
            query = query.where(Orders.id == order_id)
        if phone_number is not None:
            query = query.where(Orders.phone_number == phone_number)
        if sku is not None:
            query = query.where(Orders.sku == sku)
        if quantity is not None:
            query = query.where(Orders.quantity == quantity)

        res = await self._session.execute(query)
        return res.scalars().all()
