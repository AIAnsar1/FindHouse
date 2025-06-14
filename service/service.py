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
from models.base_model import User, Order, Address
from datetime import datetime
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton


class Service:
    def __init__(self, bot: Bot):
        self.logger_handler = LoggerHandler("Service")
        self.logger = self.logger_handler.setup_logger_handler()
        self.repository = Repository()
        self.config = Configuration()
        self.router = Router()
        self.bot = bot
    
    
    def register_bot_create_order_command_handler():
        pass
        
        
   
        
    

    