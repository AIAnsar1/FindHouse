from environs import Env, EnvError
from typing import Optional, Any
from handler import logger
from pathlib import Path


class Configuration:
    DEBUG: Optional[bool] = True
    TELEGRAM_BOT_API_TOKEN: Optional[str]
    TELEGRAM_BOT_ADMIN_ID1: Optional[int]
    TELEGRAM_BOT_ADMIN_ID2: Optional[int]
    TELEGRAM_BOT_ADMIN_ID3: Optional[int]
    TELEGRAM_ADMINS_CONTROLL_GROUP: Optional[int]
    
    TELEGRAM_TASHKENT_CHANNEL: Optional[int]
    TELEGRAM_FERGANA_CHANNEL: Optional[int]
    TELEGRAM_KOKAND_CHANNEL: Optional[int]


    DATABASE_HOST: Optional[str]
    DATABASE_PORT: Optional[int]
    DATABASE_USERNAME: Optional[str]
    DATABASE_PASSWORD: Optional[str]
    DATABASE_NAME: Optional[str]

    REDIS_HOST: Optional[str]
    REDIS_PORT: Optional[int]
    REDIS_PASSWORD: Optional[str]

    
    
    def __init__(self):
        self.env = Env()
        env_path = Path(__file__).resolve().parent.parent / ".env"
        self.env.read_env(env_path)
        self.load_all()
        


    def load_telegram(self):
        self.TELEGRAM_BOT_API_TOKEN = self.env("TELEGRAM_BOT_API_TOKEN")
        self.TELEGRAM_BOT_ADMIN_ID1 = self.env.int("TELEGRAM_BOT_ADMIN_ID1")
        self.TELEGRAM_BOT_ADMIN_ID2 = self.env.int("TELEGRAM_BOT_ADMIN_ID2")
        self.TELEGRAM_BOT_ADMIN_ID3 = self.env.int("TELEGRAM_BOT_ADMIN_ID3")
        self.TELEGRAM_ADMINS_CONTROLL_GROUP = self.env("TELEGRAM_ADMINS_CONTROLL_GROUP")
        self.TELEGRAM_TASHKENT_CHANNEL = self.env("TELEGRAM_TASHKENT_CHANNEL")
        self.TELEGRAM_FERGANA_CHANNEL = self.env("TELEGRAM_FERGANA_CHANNEL")
        self.TELEGRAM_KOKAND_CHANNEL = self.env("TELEGRAM_KOKAND_CHANNEL")
    
    
    def load_database(self):
        self.DATABASE_HOST = self.env("DATABASE_HOST")
        self.DATABASE_PORT = self.env("DATABASE_PORT")
        self.DATABASE_USERNAME = self.env("DATABASE_USERNAME")
        self.DATABASE_PASSWORD = self.env("DATABASE_PASSWORD")
        self.DATABASE_NAME = self.env("DATABASE_NAME")

    def load_redis(self):
        self.REDIS_HOST = self.env("REDIS_HOST")
        self.REDIS_PORT = self.env("REDIS_PORT")
        self.REDIS_PASSWORD = self.env("REDIS_PASSWORD")

        if self.REDIS_PASSWORD:
            redis_url = f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        else:
            redis_url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"
        return redis_url



    def load_all(self):
        try:
            self.load_telegram()
            self.load_database()
            self.load_redis()
        except EnvError as e:
            raise RuntimeError(f"Ошибка конфигурации .env: {e}")



config = Configuration()






if __name__ == "__main__":
    try:
        config = Configuration()
        print("Telegram Bot Token:", config.TELEGRAM_BOT_API_TOKEN)
        print("Telegram Bot Admin ID:", config.TELEGRAM_BOT_ADMIN_ID1)
        print("Telegram Bot Admin ID:", config.TELEGRAM_BOT_ADMIN_ID2)
        print("Telegram Bot Admin ID:", config.TELEGRAM_BOT_ADMIN_ID3)

        print("MAX_VIDEO_QUEUE_SIZE:", config.MAX_VIDEO_QUEUE_SIZE)
        print("MAX_PLAYLIST_QUEUE_SIZE:", config.MAX_PLAYLIST_QUEUE_SIZE)
        print("MAX_SOCIAL_QUEUE_SIZE:", config.MAX_SOCIAL_QUEUE_SIZE)
        print("MAX_AUDIO_QUEUE_SIZE:", config.MAX_AUDIO_QUEUE_SIZE)

        print("DEBUG MODE:", config.DEBUG)
        print("TELEGRAM_NINJA_CACHE_CHANNEL:", config.TELEGRAM_NINJA_CACHE_CHANNEL)
        print("DEBUG DEBUG_TELEGRAM_BOT_API_TOKEN:", config.DEBUG_TELEGRAM_BOT_API_TOKEN)
        print("DEBUG DEBUG_TELEGRAM_NINJA_CACHE_CHANNEL:", config.DEBUG_TELEGRAM_NINJA_CACHE_CHANNEL)

        print("Telegram API_ID:", config.API_ID)
        print("Telegram API_HASH:", config.API_HASH)

        print("Database Host:", config.DATABASE_HOST)
        print("Database Port:", config.DATABASE_PORT)
        print("Database Username:", config.DATABASE_USERNAME)
        print("Database Password:", config.DATABASE_PASSWORD)
        print("Database Name:", config.DATABASE_NAME)

        print("Redis Host:", config.REDIS_HOST)
        print("Redis Port:", config.REDIS_PORT)
        print("Redis Password:", config.REDIS_PASSWORD)

        # Проверяем URL Redis
        redis_url = config.load_redis()
        print("Redis URL:", redis_url)

    except Exception as e:
        print(f"Ошибка при загрузке конфигурации: {e}")