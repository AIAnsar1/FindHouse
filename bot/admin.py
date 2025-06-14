import asyncio, uvloop, uuid
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
from models.base_model import User, Advertisements, AdvertisementsDeliveries
from sqlalchemy.future import select
from aiogram.exceptions import TelegramRetryAfter
from sqlalchemy import delete, and_
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config.configuration import Configuration
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from uuid import UUID
from .lang import MESSAGES
from handler.logger import LoggerHandler
from repository.repository import Repository




class AdsStates(StatesGroup):
    waiting_for_ad = State()
    waiting_for_lang = State()
    waiting_for_media = State()
    waiting_for_text = State()
    waiting_for_url = State()
    waiting_for_button_text = State()
    confirm_and_send = State()


class FindHouseAdmin:
    def __init__(self):
        self.logger_handler = LoggerHandler("Ninja Admin")
        self.logger = self.logger_handler.setup_logger_handler()
        self.logger.info("Ninja Admin Initialized")
        self.repository = Repository()
        self.config = Configuration()
        self.router = Router()
        
        self.ADS_PER_PAGE = 10
        
        self.ADMIN_IDS = [
            self.config.TELEGRAM_BOT_ADMIN_ID1,
            self.config.TELEGRAM_BOT_ADMIN_ID2,
            self.config.TELEGRAM_BOT_ADMIN_ID3
        ]
        self.ADMIN_IDS = [admin_id for admin_id in self.ADMIN_IDS if admin_id is not None]
        self.ADMIN_ID1 = self.config.TELEGRAM_BOT_ADMIN_ID1
        self.ADMIN_ID2 = self.config.TELEGRAM_BOT_ADMIN_ID2
        self.ADMIN_ID3 = self.config.TELEGRAM_BOT_ADMIN_ID3
        
    
    def register_bots_admin_command_handler(self):
        self.router.message.register(self.handle_ads_command, Command("start_post_ads_"))
        self.router.message.register(self.handle_language_choice, StateFilter(AdsStates.waiting_for_lang))
        self.router.message.register(self.handle_media, StateFilter(AdsStates.waiting_for_media))
        self.router.message.register(self.handle_ad_text, StateFilter(AdsStates.waiting_for_text))
        self.router.message.register(self.handle_ad_url, StateFilter(AdsStates.waiting_for_url))
        self.router.message.register(self.handle_button_text, StateFilter(AdsStates.waiting_for_button_text))
        self.router.message.register(self.send_advertising, StateFilter(AdsStates.waiting_for_ad))
        self.router.message.register(self.my_commands, Command("get_all_posts_ads_"))
        self.router.callback_query.register(self.paginate_ads, lambda c: c.data and c.data.startswith("ads_page:"))
        self.router.message.register(self.send_advertising, StateFilter(AdsStates.waiting_for_lang))
        self.router.message.register(self.delete_ad, Command("delete_posts_ads_by_uuid_"))
        

    async def get_all_users(self, session):
        async with self.repository.session_scope() as session:
            result = await session.execute(select(User.user_id, User.language))
            return {user_id: lang for user_id, lang in result.all()}
            
    
    async def handle_ads_command(self, message: Message, state: FSMContext):
        user_id = message.from_user.id
        self.logger.info(f"ADMIN_IDS: {self.ADMIN_IDS}, user_id: {user_id}")
        self.logger.info(f"📩 Получена команда /start_post_ads_ от {user_id}")
        
        async with self.repository.session_scope() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalars().first()

            if user_id not in self.ADMIN_IDS:
                await message.answer(MESSAGES["send_link"].get(user.language, MESSAGES["send_link"]["en"]))
                return
        
        lang_kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇺🇸 English")],
        ], resize_keyboard=True, one_time_keyboard=True)
        await state.set_state(AdsStates.waiting_for_lang)
        await message.answer("🌍 Выберите язык аудитории для рассылки:", reply_markup=lang_kb)
        
    
    async def handle_language_choice(self, message: Message, state: FSMContext):
        if "Русский" in message.text:
            lang = "ru"
        elif "English" in message.text:
            lang = "en"
        else:
            await message.answer("❗️ Пожалуйста, выберите язык с клавиатуры.")
            return
        await state.update_data(target_lang=lang)
        await state.set_state(AdsStates.waiting_for_media)
        await message.answer("📸 Отправьте фото, видео или гифку для рекламы (или напишите /skip если без медиа)")
    


    async def handle_media(self, message: Message, state: FSMContext):
        media = None
        media_type = None

        if message.photo:
            media = message.photo[-1].file_id
            media_type = 'photo'
        elif message.video:
            media = message.video.file_id
            media_type = 'video'
        elif message.animation:
            media = message.animation.file_id
            media_type = 'animation'
        elif message.text and message.text.lower() == "/skip":
            media_type = 'none'
        else:
            await message.answer("❗️Пожалуйста, отправьте медиафайл или напишите /skip.")
            return

        await state.update_data(media_file_id=media, media_type=media_type)
        await state.set_state(AdsStates.waiting_for_text)
        await message.answer("📝 Введите текст рекламы.")


    async def handle_ad_text(self, message: Message, state: FSMContext):
        await state.update_data(ad_text=message.text)
        await state.set_state(AdsStates.waiting_for_url)
        await message.answer("🔗 Введите ссылку (начинается с https:// или http://).")


    async def handle_ad_url(self, message: Message, state: FSMContext):
        if not message.text.startswith("http"):
            await message.answer("❗️ Пожалуйста, введите корректную ссылку (начинается с http/https).")
            return
        await state.update_data(button_url=message.text)
        await state.set_state(AdsStates.waiting_for_button_text)
        await message.answer("📎 Введите название кнопки (например: Перейти)")


    async def handle_button_text(self, message: Message, bot: Bot, state: FSMContext):
        await state.update_data(button_text=message.text)

        data = await state.get_data()
        target_lang = data["target_lang"]
        media_file_id = data.get("media_file_id")
        media_type = data.get("media_type")
        ad_text = data.get("ad_text")
        button_url = data.get("button_url")
        button_text = data.get("button_text")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=button_text, url=button_url)]
            ])

        async with self.repository.session_scope() as session:
            # Создаем новую рекламу
            ad_uuid = str(uuid.uuid4())
            new_ad = Advertisements(
                ad_uuid=ad_uuid,
                content=ad_text,
                media_type=media_type,
                media_file_id=media_file_id,
                target_lang=target_lang,
                is_active=True
            )
            session.add(new_ad)
            await session.flush()  # Получаем ID новой записи

            users = await self.get_all_users(session)
            sent = 0

            for user_id, lang in users.items():
                if lang != target_lang or user_id in [self.ADMIN_ID1, self.ADMIN_ID2, self.ADMIN_ID3]:
                    continue
                try:
                    msg = None
                    if media_type == "photo":
                        msg = await bot.send_photo(user_id, media_file_id, caption=ad_text, reply_markup=keyboard)
                    elif media_type == "video":
                        msg = await bot.send_video(user_id, media_file_id, caption=ad_text, reply_markup=keyboard)
                    elif media_type == "animation":
                        msg = await bot.send_animation(user_id, media_file_id, caption=ad_text, reply_markup=keyboard)
                    else:
                        msg = await bot.send_message(user_id, ad_text, reply_markup=keyboard)

                    # Сохраняем информацию о доставке
                    delivery = AdvertisementsDeliveries(
                        ad_id=new_ad.id,
                        user_id=user_id,
                        message_id=msg.message_id
                    )
                    session.add(delivery)
                    sent += 1
                except Exception as e:
                    print(f"[Ошибка] Не удалось отправить {user_id}: {e}")

            await session.commit()

        await message.answer(f"✅ Реклама успешно отправлена {sent} пользователям.")
        await state.clear()


    async def send_advertising(self, ad_message: Message, bot: Bot, state: FSMContext):
        async with self.repository.session_scope() as session:
            data = await state.get_data()
            target_lang = data.get("target_lang")

            print(f"[DEBUG] Sending ad with target_lang: {target_lang}")

            users = await self.get_all_users(session)  # {user_id: lang}
            ad_uuid = str(uuid.uuid4())
            ads_by_lang = {}

            # Сохраняем рекламу для двух языков
            for lang in ["ru", "en"]:
                media_type = (
                    'photo' if ad_message.photo else
                    'video' if ad_message.video else
                    'animation' if ad_message.animation else
                    'text'
                )
                media_file_id = (
                    ad_message.photo[-1].file_id if ad_message.photo else
                    ad_message.video.file_id if ad_message.video else
                    ad_message.animation.file_id if ad_message.animation else
                    None
                )

                new_ad = Advertisements(
                    ad_uuid=ad_uuid,
                    content=ad_message.caption or ad_message.text or '',
                    media_type=media_type,
                    media_file_id=media_file_id,
                    target_lang=lang,
                )
                session.add(new_ad)
                await session.flush()  # Получаем ID новой записи
                ads_by_lang[lang] = new_ad.id

            sent = 0
            for user_id, lang in users.items():
                if lang != target_lang or user_id == self.ADMIN_ID1 and lang != target_lang or user_id == self.ADMIN_ID2 and lang != target_lang or user_id == self.ADMIN_ID3:
                    continue

                try:
                    msg = None
                    if ad_message.photo:
                        msg = await bot.send_photo(user_id, ad_message.photo[-1].file_id, caption=ad_message.caption)
                    elif ad_message.video:
                        msg = await bot.send_video(user_id, ad_message.video.file_id, caption=ad_message.caption)
                    elif ad_message.animation:
                        msg = await bot.send_animation(user_id, ad_message.animation.file_id, caption=ad_message.caption)
                    elif ad_message.text:
                        msg = await bot.send_message(user_id, ad_message.text)
                    else:
                        msg = await bot.send_message(user_id, " ")

                    sent += 1
                    delivery = AdvertisementsDeliveries(
                        ad_id=ads_by_lang[lang],
                        user_id=user_id,
                        message_id=msg.message_id
                    )
                    session.add(delivery)
                except Exception as e:
                    self.logger.error(f"❌ Не удалось отправить {user_id}: {e}")

            await session.commit()
            await ad_message.answer(f"✅ Реклама успешно отправлена {sent} пользователям.")
            await state.clear()



    def get_keyboard(self, page: int, total: int):
        buttons = []

        if page > 0:
            buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"ads_page:{page - 1}"))
        if (page + 1) * self.ADS_PER_PAGE < total:
            buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"ads_page:{page + 1}"))

        markup = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
        return markup

    def format_ads_page(self, ads: list, page: int):
        start = page * self.ADS_PER_PAGE
        end = start + self.ADS_PER_PAGE
        selected = ads[start:end]

        grouped = {}
        for ad in selected:
            grouped.setdefault(ad.ad_uuid, []).append(ad)

        ad_info = ""
        for uuid, ad_list in grouped.items():
            ad_info += f"📜 <b>UUID</b>: <code>{uuid}</code>\n"
            for ad in ad_list:
                ad_info += f"🌍 Язык: {ad.target_lang}\n📝 {ad.content}\n\n"
        return ad_info or "❗ Нет данных для отображения."

    async def my_commands(self, message: Message, state: FSMContext):
        if message.from_user.id not in [self.ADMIN_ID1, self.ADMIN_ID2, self.ADMIN_ID3]:
            await message.answer("❗️ У вас нет прав для использования этой команды.")
            return

        async with self.repository.session_scope() as session:
            result = await session.execute(
                select(Advertisements).filter(Advertisements.is_active == True)
            )
            ads = result.scalars().all()

        if not ads:
            await message.answer("❗ Нет активных рекламных сообщений.")
            return

        await state.update_data(ads=[ad.to_dict() for ad in ads])  # Приведи к dict, если модель не сериализуется
        page = 0
        ad_info = self.format_ads_page(ads, page)
        keyboard = self.get_keyboard(page, len(ads))
        await message.answer(ad_info, reply_markup=keyboard, parse_mode="HTML")

    async def paginate_ads(self, callback: types.CallbackQuery, state: FSMContext):
        page = int(callback.data.split(":")[1])
        data = await state.get_data()
        ads = [Advertisements(**ad) for ad in data.get("ads", [])]  # Преобразуем обратно в объекты, если нужно

        ad_info = self.format_ads_page(ads, page)
        keyboard = self.get_keyboard(page, len(ads))
        await callback.message.edit_text(ad_info, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()



    async def get_ads_by_lang(self, message: Message, state: FSMContext):
        if "Русский" in message.text:
            lang = "ru"
        elif "English" in message.text:
            lang = "en"
        else:
            await message.answer("❗ Пожалуйста, выберите язык с клавиатуры.")
            return

        async with self.repository.session_scope() as session:
            result = await session.execute(
                select(Advertisements)
                .filter(Advertisements.is_active == True)
                .filter(Advertisements.target_lang == lang)
            )
            ads = result.scalars().all()

        # Логируем полученные данные
        print(f"[DEBUG] Found ads: {ads}")

        await state.clear()

        if not ads:
            await message.answer(f"❗ Нет активных реклам на языке {lang}.")
            return

        ad_info = ""
        for ad in ads:
            ad_info += f"📜 **UUID**: {ad.ad_uuid}\n📝 **Текст рекламы**: {ad.content}\n🌍 **Язык**: {ad.target_lang}\n\n"

        await message.answer(f"📜 Рекламы на языке `{lang}`:\n\n{ad_info}")



    async def delete_ad(self, message: Message, state: FSMContext, bot: Bot):
        user_id = message.from_user.id
        command_parts = message.text.split()

        if len(command_parts) < 2:
            await message.answer("❌ Пожалуйста, укажите UUID объявления для удаления.")
            return

        ad_uuid = command_parts[1]

        async with self.repository.session_scope() as session:
            # Получаем все рекламы с данным UUID
            ad_results = await session.execute(
                select(Advertisements).filter_by(ad_uuid=ad_uuid)
            )
            ads = ad_results.scalars().all()

            if not ads:
                await message.answer("❌ Реклама с таким UUID не найдена.")
                return

            # Получаем все доставки этой рекламы
            deliveries_result = await session.execute(
                select(AdvertisementsDeliveries).filter(AdvertisementsDeliveries.ad_id.in_([ad.id for ad in ads]))
            )
            deliveries = deliveries_result.scalars().all()

            for delivery in deliveries:
                try:
                    await bot.delete_message(chat_id=delivery.user_id, message_id=delivery.message_id)
                except Exception as e:
                    self.logger.warning(f"❌ Не удалось удалить сообщение у {delivery.user_id}: {e}")
            # Сначала удаляем все связи с пользователями
            await session.execute(delete(AdvertisementsDeliveries).filter(AdvertisementsDeliveries.ad_id.in_([ad.id for ad in ads])))
            # Затем удаляем все записи рекламы с данным UUID
            await session.execute(delete(Advertisements).filter_by(ad_uuid=ad_uuid))
            await session.commit()
            await message.answer(f"✅ Реклама с UUID {ad_uuid} удалена и сообщения удалены из чатов.")