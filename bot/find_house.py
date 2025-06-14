import asyncio, uvloop, re, os, psutil
from aiogram import Router, Dispatcher, Bot, types, F
from aiogram.client.default import DefaultBotProperties
from handler.logger import LoggerHandler
from config.configuration import Configuration
from contextlib import asynccontextmanager
from database.database import DataBase
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from models.base_model import User
from sqlalchemy.future import select
from aiogram.exceptions import TelegramRetryAfter
from sqlalchemy import delete, and_
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import StateFilter, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from .lang import MESSAGES
from datetime import datetime
from handler.logger import LoggerHandler
from aiogram.types.input_file import FSInputFile
from sqlalchemy import update
from repository.repository import Repository
from aiogram.fsm.state import State, StatesGroup
from service.service import Service
from service.rent_home_service import RentHomeService
from service.search_sale_rent_service import SearchSaleRentHomeService
from service.channel_publish_filter_service import ChannelPublishFilterService
from .admin import AdsStates, FindHouseAdmin
from urllib.parse import urlparse, parse_qs
from models.base_model import User, Address, Order
from pathlib import Path
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext





class FindHouse(FindHouseAdmin):
    def __init__(self):
        super().__init__()
        
        self.logger_handler = LoggerHandler()
        self.logger = self.logger_handler.setup_logger_handler()
        self.logger.info("Ninja Downloader Initialized")

        self.config = Configuration()

        self.session = AiohttpSession(api=TelegramAPIServer.from_base("http://localhost:8081"))
        self.router = Router()
        self.dp = Dispatcher()
        self.config = Configuration()
        
        self.TOKEN = self.config.TELEGRAM_BOT_API_TOKEN

        self.bot = Bot(token=self.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML), session=self.session)
        self.repository = Repository()
        self.service = Service(self.bot)
        self.rent_home_service = RentHomeService(self.router, self.bot)
        # self.sale_home_service = SaleHomeService(self.bot)
        # self.search_sale_rent_service = SearchSaleRentHomeService(self.bot)
        self.setup()
        

    def setup(self):
        try:
            self.dp.include_router(self.router)
            self.register_bots_admin_command_handler()
            self.register_bots_command_handler()
            self.rent_home_service.register_rent_home_service_commands()
            self.logger.info("Bot setup completed successfully")
        except Exception as e:
            self.logger.error("Error Setup Bot")
            import traceback
            print(traceback.format_exc())
            self.logger.error(f"Exception in setup_bot: {e}")

    def register_bots_command_handler(self):
        self.router.message.register(self.start_handler, F.text == "/start")
        self.router.callback_query.register(self.set_language_callback, F.data.startswith("set_language:"))
        
        self.router.callback_query.register(self.handle_rent_creation, F.data.startswith("create_rent_home:"))
        
        self.router.callback_query.register(self.handle_search, F.data.startswith("search_rent_sale_home:"))
        
        self.router.message.register(self.message_handler, StateFilter(None), F.text)

        
    
    
    async def get_user_language(self, user_id: int) -> str:
        async with self.repository.session_scope() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id).limit(1).execution_options(autocommit=True))
            user = result.scalar_one_or_none()

            if user and user.language:
                return user.language
            return None

    async def add_user_to_db(self, message: Message, session, language: str = None):
        user_info = await self.bot.get_chat(message.from_user.id)
        phone = None

        if hasattr(message, 'contact') and message.contact:
            phone = message.contact.phone_number
        language = language or 'en'
        user_data = {
            "user_id": message.from_user.id,
            "name": message.from_user.first_name,
            "surname": message.from_user.last_name,
            "username": message.from_user.username,
            "date": datetime.now(),
            "phone": phone,
            "bio": user_info.bio,
            "language": language,  # Устанавливаем язык сразу
        }

        try:
            user = User(**user_data)
            session.add(user)
            await session.commit()
            self.logger.info(f"User {message.from_user.id} added to database with language {language}")
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Error adding user to database: {e}")
            raise e

    async def set_user_language(self, user_id: int, language: str):
        self.logger.info(f"Setting language {language} for user {user_id}")
        async with self.repository.session_scope() as session:
            # Сначала проверяем существование пользователя
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                self.logger.error(f"User {user_id} not found")
                return False
            user.language = language
            await session.commit()
            result = await session.execute(select(User).filter(User.user_id == user_id))
            updated_user = result.scalar_one_or_none()
            
            if updated_user and updated_user.language == language:
                self.logger.info(f"Successfully updated language for user {user_id}")
                return True
            self.logger.error(f"Failed to update language for user {user_id}")
            return False
        

    async def start_handler(self, message: types.Message):
        user_id = message.from_user.id

        async with self.repository.session_scope() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalars().first()

            if not user:
                detected_language = await self.get_user_language(user_id)
                await self.add_user_to_db(message, session, language=None)  # язык пока None
                # Показываем кнопки выбора языка
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_language:ru"),
                    InlineKeyboardButton(text="🇺🇸 English", callback_data="set_language:en"),
                    InlineKeyboardButton(text="🇺🇿 Uzbek", callback_data="set_language:uz"),
                ]])
                await message.answer("Выберите язык / Choose your language / Tilni tanlang:", reply_markup=kb)
                return

            if not user.language:
                # Язык не выбран
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_language:ru"),
                    InlineKeyboardButton(text="🇺🇸 English", callback_data="set_language:en"),
                    InlineKeyboardButton(text="🇺🇿 Uzbek", callback_data="set_language:uz"),
                ]])
                await message.answer("Выберите язык / Choose your language / Tilni tanlang:", reply_markup=kb) # select_action
                return
            await message.answer(MESSAGES["select_action"].get(user.language, MESSAGES["select_action"]["en"]), reply_markup=self.action_menu_keyboard(user.language))
            
        
    async def set_language_callback(self, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        language = callback_query.data.split(":")[1]

        async with self.repository.session_scope() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalars().first()

            if user:
                user.language = language
                await session.commit() # lang_selected
        await callback_query.answer(MESSAGES["lang_selected"].get(user.language, MESSAGES["select_action"]["en"]))
        await callback_query.message.edit_text(MESSAGES["lang_selected"].get(language, MESSAGES["lang_selected"]["en"]))
        await self.bot.send_message(user_id, MESSAGES["select_action"].get(user.language, MESSAGES["select_action"]["en"]), reply_markup=self.action_menu_keyboard(language))
            
    
    def action_menu_keyboard(self, language: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=MESSAGES["rent_home"].get(language, MESSAGES["rent_home"]["en"]), callback_data="create_rent_home:"),
            InlineKeyboardButton(text=MESSAGES["search_home"].get(language, MESSAGES["search_home"]["en"]), callback_data="search_rent_sale_home:")
        ]])

    
    async def message_handler(self, message: Message):
        user_id = message.from_user.id
        

        async with self.repository.session_scope() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalar_one_or_none()
            
            if not user or not user.language:
                # Если язык не установлен, предлагаем выбрать язык
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_language:ru"),
                    InlineKeyboardButton(text="🇺🇸 English", callback_data="set_language:en"),
                    InlineKeyboardButton(text="🇺🇿 Uzbek", callback_data="set_language:uz"),
                ]])
                await message.answer("Выберите язык / Choose your language / Tilni tanlang:", reply_markup=kb)
                return
            user_language = user.language
            await self.bot.send_message(user_id,MESSAGES["select_action"].get(user.language, MESSAGES["select_action"]["en"]), reply_markup=self.action_menu_keyboard(user_language))

        
    
    async def handle_rent_creation(self, callback_query: CallbackQuery, state: FSMContext):
        await self.rent_home_service.start_rent(callback_query, state)
    
    async def handle_search(self, message: Message):
        # self.search_sale_rent_service.
        pass
    
    
    
        


    async def start_bot(self):
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.logger.error(f"[ ERROR ]: Starting Bot {e}")
            raise
    











async def main():
    ninja = FindHouse()
    await ninja.start_bot()




if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    uvloop.install()
    asyncio.run(main())