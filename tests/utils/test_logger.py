"""Tests for Logger."""

import logging
from context_kiwi.utils.logger import Logger


class TestLogger:
    """Test Logger."""
    
    def test_logger_creation(self):
        """Should create logger instance."""
        logger = Logger("test", level="INFO")
        assert logger is not None
    
    def test_logger_levels(self):
        """Should support different log levels."""
        logger_debug = Logger("test", level="DEBUG")
        assert logger_debug.logger.level == logging.DEBUG
        
        logger_error = Logger("test", level="ERROR")
        assert logger_error.logger.level == logging.ERROR
    
    def test_logger_methods(self):
        """Should have logging methods."""
        logger = Logger("test")
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
