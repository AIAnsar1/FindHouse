import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from handler.logger import LoggerHandler
from config.configuration import Configuration
from models.base_model import Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine




class DataBase(Configuration):
    def __init__(self):
        super().__init__()
        self.logger_handler = LoggerHandler("YouTube")
        self.logger = self.logger_handler.setup_logger_handler()
        self.logger.info(f"DataBase Initialized")
        self.engine = None
        self.SessionLocal: Optional[sessionmaker] = None
        self.session: Optional[AsyncSession] = None

    async def create_connect(self):
        """Создаём подключение к базе данных с асинхронной сессией."""
        required = [
            self.DATABASE_USERNAME,
            self.DATABASE_PASSWORD,
            self.DATABASE_HOST,
            self.DATABASE_PORT,
            self.DATABASE_NAME,
        ]
        if not all(required):
            raise RuntimeError("[ ETA ]: ❌ Отсутствуют переменные окружения для подключения к базе данных")

        try:
            # Формируем строку подключения для асинхронного движка
            db_url = f"postgresql+psycopg://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            self.engine = create_async_engine(db_url, echo=True)  # Используем асинхронный движок
            self.SessionLocal = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            self.logger.info("✅ Подключение к базе данных установлено")
        except SQLAlchemyError as e:
            self.logger.error(f"❌ Ошибка при подключении к базе данных: {e}")
            raise RuntimeError(f"Ошибка подключения к базе данных: {e}")

    async def get_session(self) -> AsyncSession:
        """Получаем асинхронную сессию для работы с базой данных."""
        if self.SessionLocal is None:
            raise RuntimeError("[ ETA ]: 💡 Необходимо сначала вызвать create_connect()")

        self.session = self.SessionLocal()  # Получаем асинхронную сессию
        return self.session

    async def close_connect(self):
        """Закрываем подключение и сессию."""
        if self.session:
            await self.session.close()  # Закрываем асинхронную сессию
            self.logger.info("🛑 Сессия закрыта")
        if self.engine:
            await self.engine.dispose()  # Закрываем асинхронное соединение
            self.logger.info("🧹 Соединение с БД закрыто")

    async def create_tables(self):
        """Создаём все таблицы в базе данных."""
        if self.engine is None:
            raise RuntimeError("[ ETA ]: 💡 Сначала вызови create_connect() перед созданием таблиц.")

        try:
            # Используем асинхронное создание таблиц
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)  # Асинхронное создание таблиц
            self.logger.info("✅ Все таблицы успешно созданы в базе данных")
        except SQLAlchemyError as e:
            self.logger.error(f"❌ Ошибка при создании таблиц: {e}")


async def main():
    db = DataBase()
    await db.create_connect()
    # session = await db.get_session()
    await db.create_tables()
    await db.close_connect()


# Запуск асинхронной функции
if __name__ == "__main__":
    asyncio.run(main())