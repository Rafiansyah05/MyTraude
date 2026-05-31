"""
Structured logging setup for the trading bot.
Provides consistent logging across all modules.
"""

import logging
import sys
from typing import Optional
from config.settings import settings


class StructuredLogger:
    """Centralized logger with structured output."""
    
    _loggers: dict = {}
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get or create a logger with structured formatting."""
        if name in StructuredLogger._loggers:
            return StructuredLogger._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
        
        # Create console handler using the standard text stream
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

        # Set encoding only if supported by the handler
        if hasattr(console_handler, 'encoding') and console_handler.encoding is None:
            try:
                console_handler.encoding = 'utf-8'
            except Exception:
                pass

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s | %(name)-25s | %(levelname)-8s | %(funcName)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        
        # Remove duplicate handlers
        logger.handlers.clear()
        logger.addHandler(console_handler)
        
        # Optional file logging
        if settings.LOG_FILE_PATH:
            try:
                import os
                os.makedirs(os.path.dirname(settings.LOG_FILE_PATH), exist_ok=True)
                file_handler = logging.FileHandler(settings.LOG_FILE_PATH, encoding='utf-8')
                file_handler.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Failed to setup file logging: {e}")
        
        StructuredLogger._loggers[name] = logger
        return logger


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get logger."""
    return StructuredLogger.get_logger(name)
