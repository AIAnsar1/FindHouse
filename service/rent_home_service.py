import os, asyncio
from handler.logger import LoggerHandler
from aiogram.types import Message
from repository.repository import Repository
from sqlalchemy import select, and_
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
from sqlalchemy import select, and_, or_
from bot.lang import MESSAGES



class RentHomeStates(StatesGroup):
    # ────────── общие поля объявления ──────────
    waiting_for_title       = State()
    waiting_for_description = State()
    waiting_for_photos      = State()
    waiting_for_price       = State()
    waiting_for_phone       = State()

    # ────────── адрес до махалли + доп. вручную ──────────
    waiting_for_state       = State()  # вилоят
    waiting_for_region      = State()  # туман
    waiting_for_city        = State()  # город
    waiting_for_address_line= State()  # подъезд, этаж, квартира и пр.

    waiting_for_user_confirmation = State()
    waiting_for_admin_confirmation = State()
    waiting_for_admin_reason = State()




class RentHomeService:
    MAX_PHOTOS = 7
    
    def __init__(self, router: Router, bot: Bot):
        self.logger_handler = LoggerHandler()
        self.logger = self.logger_handler.setup_logger_handler()
        self.logger.info("Sale Home Service Initialized")
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
        
    def register_rent_home_service_commands(self):
        self.router.message.register(self.title, RentHomeStates.waiting_for_title)
        self.router.message.register(self.description, RentHomeStates.waiting_for_description)
        self.router.message.register(self.photos, RentHomeStates.waiting_for_photos, F.photo)
        self.router.message.register(self.price, RentHomeStates.waiting_for_price)
        self.router.message.register(self.phone, RentHomeStates.waiting_for_phone)

        self.router.message.register(self.state, RentHomeStates.waiting_for_state)
        self.router.message.register(self.region, RentHomeStates.waiting_for_region)
        self.router.message.register(self.city, RentHomeStates.waiting_for_city)
        self.router.message.register(self.address_line, RentHomeStates.waiting_for_address_line)

        self.router.callback_query.register(self.confirm_submission, RentHomeStates.waiting_for_user_confirmation, F.data.startswith("rent_confirm:"))
        self.router.callback_query.register(self.admin_decision,F.data.startswith("admin_rent:"))
        self.router.message.register(self.admin_rejection_reason, RentHomeStates.waiting_for_admin_reason)
        

    
    async def get_user_language(self, user_id: int) -> str:
        async with self.repository.session_scope() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id).limit(1).execution_options(autocommit=True))
            user = result.scalar_one_or_none()

            if user and user.language:
                return user.language
            return None
    
    async def start_rent(self, callback_query: CallbackQuery, state: FSMContext):
        user_id = callback_query.from_user.id
        user_language = await self.get_user_language(user_id)
        await callback_query.message.answer(MESSAGES["title"].get(user_language, MESSAGES["title"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_title)

    async def title(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(title=msg.text)
        await msg.answer(MESSAGES["description"].get(user_language, MESSAGES["description"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_description)

    async def description(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(description=msg.text)
        await msg.answer(MESSAGES["photo"].get(user_language, MESSAGES["photo"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_photos)

    async def photos(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        data = await state.get_data()
        photos = data.get("photos", [])

        photos.append(msg.photo[-1].file_id)
        await state.update_data(photos=photos)
        if photos:
            await msg.answer(MESSAGES["price"].get(user_language, MESSAGES["price"]["en"]))
            await state.set_state(RentHomeStates.waiting_for_price)

    async def price(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(price=msg.text.strip())
        await msg.answer(MESSAGES["phone"].get(user_language, MESSAGES["phone"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_phone)

    async def phone(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(phone=msg.text.strip())
        await msg.answer(MESSAGES["state"].get(user_language, MESSAGES["state"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_state)

    async def state(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(state=msg.text.strip())
        await msg.answer(MESSAGES["region"].get(user_language, MESSAGES["region"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_region)

    async def region(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(region=msg.text.strip())
        await msg.answer(MESSAGES["city"].get(user_language, MESSAGES["city"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_city)

    async def city(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(city=msg.text.strip())
        await msg.answer(MESSAGES["address"].get(user_language, MESSAGES["address"]["en"]))
        await state.set_state(RentHomeStates.waiting_for_address_line)


    async def address_line(self, msg: Message, state: FSMContext):
        user_id = msg.from_user.id
        user_language = await self.get_user_language(user_id)
        await state.update_data(address_line=msg.text.strip())
        data = await state.get_data()
        preview = (
            f"<b>🏡 Название:</b> {data['title']}\n"
            f"<b>📄 Описание:</b> {data['description']}\n"
            f"<b>💰 Цена:</b> {data['price']} сум\n"
            f"<b>📞 Телефон:</b> {data['phone']}\n"
            f"<b>🌍 Адрес:</b> {data['state']}, {data['region']}, {data['city']}, {data['address_line']}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=MESSAGES["rent_confrim_yes"].get(user_language, MESSAGES["rent_confrim_yes"]["en"]), callback_data="rent_confirm:yes")],
                [InlineKeyboardButton(text=MESSAGES["rent_confrim_no"].get(user_language, MESSAGES["rent_confrim_no"]["en"]), callback_data="rent_confirm:no")]
            ]
        )
        media_group = [InputMediaPhoto(media=pid) for pid in data["photos"]]
        media_group[-1].caption = preview
        media_group[-1].parse_mode = "HTML"
        await msg.answer_media_group(media=media_group)
        await msg.answer("Проверьте данные и подтвердите отправку:", reply_markup=kb)
        await state.set_state(RentHomeStates.waiting_for_user_confirmation)

    async def confirm_submission(self, call: CallbackQuery, state: FSMContext):
        if call.data.endswith("no"):
            await call.message.answer("❌ Хорошо, начните заново /rent")
            return await state.clear()
        data = await state.get_data()
        async with self.repository.session_scope() as session:
            address = Address(
                state=data['state'],
                region=data['region'],
                city=data['city'],
                address_line=data['address_line']
            )
            session.add(address)
            await session.flush()
            order = Order(
                title=data['title'],
                description=data['description'],
                photos="|".join(data['photos']),
                price=data['price'],
                phone=data['phone'],
                user_id=call.from_user.id,
                address_id=address.id,
                type=OrderType.RENT,
                status=OrderStatus.WAITING,
            )
            session.add(order)
            await session.commit()
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_rent:approve:{order.id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_rent:reject:{order.id}")
                ]
            ]
        )
        media_group = [
            InputMediaPhoto(media=photo_id) for photo_id in data["photos"]
        ]
        media_group[-1].caption = (
            "<b>НОВОЕ ОБЪЯВЛЕНИЕ</b>\n" +
            f"<b>ID:</b> {order.id}\n"
            f"<b>Пользователь:</b> {call.from_user.id}\n\n"
            f"<b>🏡 Название:</b> {data['title']}\n"
            f"<b>📄 Описание:</b> {data['description']}\n"
            f"<b>💰 Цена:</b> {data['price']} сум\n"
            f"<b>📞 Телефон:</b> <code>{data['phone']}</code>\n"
            f"<b>🌍 Адрес:</b> {data['state']}, {data['region']}, {data['city']}, {data['address_line']}"
        )
        media_group[-1].parse_mode = "HTML"
        await self.bot.send_media_group(
            chat_id=self.config.TELEGRAM_ADMINS_CONTROLL_GROUP,
            media=media_group,
        )
        await self.bot.send_message(chat_id=self.config.TELEGRAM_ADMINS_CONTROLL_GROUP, text="Выберите действие:", reply_markup=admin_kb)
        await call.message.answer("✅ Объявление отправлено на модерацию!")
        await state.set_state(RentHomeStates.waiting_for_admin_confirmation)

    async def admin_decision(self, call: CallbackQuery, state: FSMContext):
        _, decision, order_id = call.data.split(":")
        async with self.repository.session_scope() as s:
            order = await s.get(Order, int(order_id))
            if not order:
                return await call.answer("Не найдено", show_alert=True)

            if decision == "approve":
                order.status = OrderStatus.APPROVED
                await s.commit()

                # ─── корректно обновляем сообщение в чате админов ───
                approve_tag = "\n\n<b>✅ Одобрено</b>"
                if call.message.caption:                         # это медиасообщение
                    await call.message.edit_caption(
                        call.message.caption + approve_tag,
                        parse_mode="HTML"
                    )
                elif call.message.text:                          # это обычный текст
                    await call.message.edit_text(
                        call.message.text + approve_tag,
                        parse_mode="HTML"
                    )
                else:  # совсем экзотический случай – просто отправим новое
                    await call.message.answer(approve_tag, parse_mode="HTML")

                # уведомляем пользователя
                await self.bot.send_message(
                    order.user_id,
                    "🎉 Ваше объявление одобрено администрацией!"
                )

                # публикуем сразу в нужный канал
                await self._publish_single(order)
                return

            # ------------- отклонение -------------
            await state.update_data(order_id=order_id)
            await call.message.answer("✏️ Причина отказа?")
            await state.set_state(RentHomeStates.waiting_for_admin_reason)

    
    async def admin_rejection_reason(self, msg: Message, state: FSMContext):
        data = await state.get_data()
        reason = msg.text.strip()
        order_id = int(data["order_id"])

        async with self.repo.session_scope() as s:
            order = await s.get(Order, order_id)
            if not order:
                return await msg.answer("⚠️ Объявление не найдено.")

            order.status = OrderStatus.REJECTED
            await s.commit()

        await msg.answer("❌ Отказ оформлен.")
        await self.bot.send_message(
            order.user_id,
            f"😔 Объявление отклонено.\n📌 Причина: <i>{reason}</i>",
            parse_mode="HTML"
        )
        await state.clear()

    
    
    
    async def _publish_single(self, order: Order):
        # 1. берём новую сессию и подгружаем адрес «жадно»
        async with self.repository.session_scope() as s:
            order = (await s.execute(
                select(Order)
                .options(selectinload(Order.address))     # eager‑load address
                .where(Order.id == order.id)
            )).scalar_one()

            # 2. детектируем город
            city_key = self._detect_city(order.address.state, order.address.city)
            channel  = self.CITY_CHANNEL.get(city_key)
            if not channel:
                return                                  # нет подходящего канала

            # 3. публикуем альбом
            await self._send_album(order, channel)

            # 4. помечаем как опубликованное
            order.is_published  = True
            order.published_at  = datetime.utcnow()
            await s.commit()

    async def run_once(self):
        """фоновый вызов, чтобы добрать всё, что не опубликовалось"""
        async with self.repo.session_scope() as s:
            for key, channel in self.CITY_CHANNEL.items():
                variants = self.CITY_VARIANTS[key]
                stmt = (
                    select(Order)
                    .join(Order.address)
                    .options(selectinload(Order.address))
                    .where(
                        Order.status == OrderStatus.APPROVED,
                        Order.is_published.is_(False),
                        or_(
                            func.lower(Address.state).in_(variants),
                            func.lower(Address.city ).in_(variants),
                        )
                    )
                )
                for order in (await s.execute(stmt)).scalars():
                    try:
                        await self._send_album(order, channel)
                        order.is_published = True
                        order.published_at = datetime.utcnow()
                    except Exception as e:
                        self.log.warning(f"Publish fail #{order.id}: {e}")
            await s.commit()

    # ───────── утилиты ─────────
    def _detect_city(self, state: str, city: str) -> str | None:
        val = (state or city or "").lower()
        for key, variants in self.CITY_VARIANTS.items():
            if any(v in val for v in variants):
                return key
        return None

    async def _send_album_to_admin(self, order: Order, data: dict):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton("✅ Одобрить",  callback_data=f"admin_rent:approve:{order.id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_rent:reject:{order.id}")
            ]]
        )
        media = [InputMediaPhoto(pid) for pid in data["photos"]]
        media[-1].caption = (
            "<b>НОВОЕ ОБЪЯВЛЕНИЕ</b>\n"
            f"<b>ID:</b> {order.id}\n"
            f"<b>Пользователь:</b> {order.user_id}\n\n"
            f"<b>🏡 Название:</b> {order.title}\n"
            f"<b>📄 Описание:</b> {order.description}\n"
            f"<b>💰 Цена:</b> {order.price} сум\n"
            f"<b>📞 Телефон:</b> <code>{order.phone}</code>\n"
            f"<b>🌍 Адрес:</b> {order.address.state}, {order.address.city}, {order.address.address_line}"
        )
        media[-1].parse_mode = "HTML"
        await self.bot.send_media_group(self.cfg.TELEGRAM_ADMINS_CONTROLL_GROUP, media)
        await self.bot.send_message(self.cfg.TELEGRAM_ADMINS_CONTROLL_GROUP,"Выберите действие:", reply_markup=kb)

    async def _send_album(self, order: Order, channel_id: int):
        photos = order.photos.split("|")
        media  = [InputMediaPhoto(media=pid) for pid in photos]
        media[-1].caption = (
            f"<b>🏡 {order.title}</b>\n"
            f"{order.description}\n\n"
            f"<b>💰 Цена:</b> {order.price} сум\n"
            f"<b>📞 Телефон:</b> <code>{order.phone}</code>\n"
            f"<b>📍 Адрес:</b> {order.address.state}, {order.address.city}, {order.address.address_line}"
        )
        media[-1].parse_mode = "HTML"
        await self.bot.send_media_group(channel_id, media)
































