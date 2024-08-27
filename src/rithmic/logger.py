import logging
import sys

class Logger:
    def __init__(self, level: int = logging.INFO):
        self.logger = logging.getLogger("default_logger")
        self.logger.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        if not self.logger.hasHandlers():
            self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

logger = Logger(level=logging.DEBUG).get_logger()
