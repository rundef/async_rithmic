import logging
import sys

# Create a Logger class to set up logging configurations
class Logger:
    def __init__(self, level: int = logging.INFO):
        """
        Initialize a logger that outputs to stdout.

        Args:
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG). Default is INFO.
        """
        self.logger = logging.getLogger("default_logger")
        self.logger.setLevel(level)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Console handler for stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Ensure no duplicate handlers
        if not self.logger.hasHandlers():
            self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

# Instantiate the logger at the module level so it can be used directly
logger = Logger(level=logging.DEBUG).get_logger()
