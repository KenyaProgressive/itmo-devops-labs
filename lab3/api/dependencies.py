from typing import Annotated

from fastapi import Depends

from service.orders_service import OrderService

OrderServiceDep = Annotated[OrderService, Depends(OrderService)]
