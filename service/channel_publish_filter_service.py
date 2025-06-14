import os, asyncio
from handler.logger import LoggerHandler
from aiogram.types import Message
from repository.repository import Repository
from sqlalchemy import select, and_, or_
from models.base_model import User
from bot.lang import MESSAGES
from aiogram.types.input_file import FSInputFile
from config.configuration import Configuration
from aiogram import Bot, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import urlparse, parse_qs
from models.base_model import User, Order, Address, OrderType, OrderStatus
from datetime import datetime
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Router, Dispatcher, Bot, types, F
from aiogram.types import InputMediaPhoto
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import selectinload


class ChannelPublishFilterService:
    def __init__(self, router: Router, bot: Bot):
        self.logger_handler = LoggerHandler()
        self.logger = self.logger_handler.setup_logger_handler()
        self.logger.info("Channel Publish Filter Service Initialized")
        self.bot = bot
        self.router = router
        self.config = Configuration()
        self.repository = Repository()
        
        self.CITY_CHANNEL = {
            "tashkent": self.config.TELEGRAM_TASHKENT_CHANNEL,
            "fergana": self.config.TELEGRAM_FERGANA_CHANNEL,
            "kokand": self.config.TELEGRAM_KOKAND_CHANNEL,
        }
        self.CITY_VARIANTS = {
            "tashkent": ("Ташкент", "ташкент", "Тошкент", "тошкент"),
            "fergana":  ("Фергана",  "фергана",  "фаргона", "Фаргона"),
            "kokand":   ("Коканд",   "коканд",    "Кукон",  "кукон"),
        }
        
    def register_channel_publish_filter_service_handler(self):
        pass
    
    
    
    async def run_once(self):
        async with self.repository.session_scope() as session:
            for city_keys, channel_id in self.CITY_CHANNEL.items():
                variants = self.CITY_VARIANTS[city_keys]
                stmt = (
                    select(Order).join(Order.address).options(selectinload(Order.address)).where(Order.status == OrderStatus.APPROVED, Order.is_published.is_(False), or_(*[
                        func.lower(Address.state).in_(variants),
                        func.lower(Address.city).in_(variants),
                    ])).order_by(Order.id).limit(1)
                )
                orders = (await session.execute(stmt)).scalars().all()
                
                for order in orders:
                    try:
                        await self._send_album(order, channel_id)
                        order.is_published = True
                        order.published_at = datetime.utcnow()
                        self.logger.info(f"Order {order.id} sent to {city_keys} channel")
                    except Exception as e:
                        self.logger.warning(f"Failed publish #{order.id}: {e}")
            await session.commit()
    
    
    async def _send_album(self, order: Order, channel_id: int):
        photos = order.photos.split("|")
        media = [InputMediaPhoto(pid) for pid in photos]
        media[-1].caption = (
            f"<b>🏡 {order.title}</b>\n"
            f"{order.description}\n\n"
            f"<b>💰 Цена:</b> {order.price} сум\n"
            f"<b>📞 Телефон:</b> <code>{order.phone}</code>\n"
            f"<b>📍 Адрес:</b> {order.address.state}, {order.address.city}, {order.address.address_line}"
        )
        media[-1].parse_mode = "HTML"
        await self.bot.send_media_group(channel_id, media)
        

    
































