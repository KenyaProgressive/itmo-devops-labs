from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import ClassVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)

from config import POSTGRES_URL
from db.base import Base


class DBMaster:

    _engine: ClassVar[AsyncEngine] = create_async_engine(
        url=POSTGRES_URL, pool_pre_ping=True, pool_size=10
    )

    _session_maker = async_sessionmaker(
        bind=_engine, autoflush=True, expire_on_commit=False
    )

    @classmethod
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_maker() as session:
            yield session

    @classmethod
    async def create_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
