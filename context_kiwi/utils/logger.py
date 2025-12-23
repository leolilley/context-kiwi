"""
Logger
Structured logging for Context Kiwi MCP Server.
"""

import logging
import sys
from typing import Optional


class Logger:
    """Simple logger wrapper with structured logging support."""
    
    def __init__(self, name: str = "context-kiwi", level: str = "DEBUG"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        
        # Only add handler if none exist
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def debug(self, message: str, extra: Optional[dict] = None):
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, extra: Optional[dict] = None):
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, extra: Optional[dict] = None):
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, extra: Optional[dict] = None):
        self.logger.error(message, extra=extra)
    
    def isEnabledFor(self, level: int) -> bool:
        return self.logger.isEnabledFor(level)

