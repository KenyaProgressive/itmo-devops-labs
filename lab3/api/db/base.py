from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import (DeclarativeBase, Mapped, MappedAsDataclass,
                            mapped_column)
from sqlalchemy.sql.functions import func
from sqlalchemy import text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.types import UUID as SA_UUID


class Base(MappedAsDataclass, DeclarativeBase):

    id: Mapped[UUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"), init=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), init=False
    )
