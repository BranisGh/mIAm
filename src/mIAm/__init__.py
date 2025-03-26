import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style
from logging.handlers import RotatingFileHandler


ROOT = Path(__file__).absolute().parent 


class ColoredFormatter(logging.Formatter):
    """Custom log formatter with color support."""
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        return f"{color}{log_message}{Style.RESET_ALL}"

def setup_logger(console_logging_enabled=False, log_level=logging.INFO):
    """
    Set up a comprehensive logging system with color support.
    
    Args:
        console_logging_enabled (bool): Enable console logging.
        log_level (int): Logging level (default: logging.INFO).
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    # Initialize colorama
    init(autoreset=True)

    # Create logs directory
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate unique log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"pipeline_log_{timestamp}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # Create logger
    logger = logging.getLogger("miam_logger")
    logger.setLevel(log_level)
    logger.handlers.clear()
    
    # File formatter (non-colored for log files)
    file_formatter = logging.Formatter(
        "[%(asctime)s: %(levelname)s: %(module)s: %(message)s]",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Colored console formatter
    console_formatter = ColoredFormatter(
        "[%(asctime)s: %(levelname)s: %(module)s: %(message)s]",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Rotating File Handler
    file_handler = RotatingFileHandler(
        log_filepath, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # Console Handler (if enabled)
    if console_logging_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
    
    # Log initial setup information
    logger.info(f"Logging initialized. Log file: {log_filepath}")
    
    return logger