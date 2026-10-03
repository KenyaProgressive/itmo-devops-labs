from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import DBMaster
from dto.orders import OrderCreateDTO, OrderDTO, OrdersListFilterDTO
from repository.orders_repository import OrdersRepository


class OrderService:

    def __init__(self, session: AsyncSession = Depends(DBMaster.get_session)):
        self._session = session
        self._repo = OrdersRepository(self._session)

    async def make_order(self, order: OrderCreateDTO) -> UUID:
        order_id = await self._repo.insert_order_data(order=order.model_dump())
        await self._session.commit()
        return order_id

    async def get_orders(self, filters: OrdersListFilterDTO) -> list[OrderDTO]:
        orders = await self._repo.get_orders_data(
            phone_number=filters.phone_number,
            sku=filters.sku,
            quantity=filters.quantity,
            order_id=filters.order_id,
        )

        if len(orders) == 0:
            return []

        if len(orders) == 1:
            return OrderDTO.model_validate(orders[0])

        return [OrderDTO.model_validate(order) for order in orders]
