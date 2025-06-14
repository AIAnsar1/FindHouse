import sys, logging
from pathlib import Path
from datetime import datetime
from config.configuration import config




class LoggerHandler:
    def __init__(self, name: str = "[ ETA ]", log_to_file: bool = True, log_dir: str = "../logs"):
        self.name = name
        self.log_to_file = log_to_file
        self.log_dir = log_dir
        self.config = config  # Используем существующий экземпляр конфигурации

    def setup_logger_handler(self) -> logging.Logger:
        """Setup logger with configurable debug mode and file logging"""
        logger = logging.getLogger(self.name)

        # Get debug mode from configuration
        log_level = logging.DEBUG if self.config.DEBUG else logging.INFO
        logger.setLevel(log_level)

        if not logger.handlers:
            formatter = logging.Formatter("[ ETA ]: %(levelname)s | %(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(log_level)
            logger.addHandler(console_handler)

            # File handler
            if self.log_to_file:
                Path(self.log_dir).mkdir(parents=True, exist_ok=True)
                log_filename = Path(self.log_dir) / f"{datetime.now().strftime('%Y-%m-%d')}.log"
                file_handler = logging.FileHandler(log_filename, encoding="utf-8")
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level)
                logger.addHandler(file_handler)

        return logger