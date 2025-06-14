
from handler.logger import LoggerHandler
from contextlib import asynccontextmanager
from database.database import DataBase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.base_model import User


class Repository:
    def __init__(self):
        self.logger_handler = LoggerHandler("Repository Initialized")
        self.logger = self.logger_handler.setup_logger_handler()
        self.logger.info("Repository Initialized")
        self.database = DataBase()

    @asynccontextmanager
    async def session_scope(self):
        """Асинхронный контекстный менеджер для сессии."""
        await self.database.create_connect()
        session: AsyncSession = await self.database.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await self.database.engine.dispose()