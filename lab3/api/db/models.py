from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Integer, String, Boolean

from db.base import Base


class Orders(Base):
    __tablename__ = "orders"

    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sku: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    quantity: Mapped[int] = mapped_column(Integer, server_default="1")
    is_processed: Mapped[bool] = mapped_column(Boolean, server_default="false")


class Products(Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
