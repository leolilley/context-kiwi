"""
Settings
Configuration management for Context Kiwi MCP Server.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Production URL (Fly.io deployment)
PROD_URL = "https://context-kiwi.fly.dev"


def get_base_url() -> str:
    """
    Get the base URL for directive downloads.
    
    Priority:
    1. CONTEXT_KIWI_URL env var (explicit override)
    2. Auto-detect: production vs localhost based on ENVIRONMENT
    """
    # Explicit override always wins
    explicit_url = os.getenv("CONTEXT_KIWI_URL")
    if explicit_url:
        return explicit_url.rstrip("/")
    
    # Auto-detect based on environment
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return PROD_URL
    
    # Development: use localhost with configured port
    port = int(os.getenv("MCP_PORT", os.getenv("HTTP_PORT", "8000")))
    return f"http://localhost:{port}"


@dataclass
class Config:
    """Server configuration."""
    environment: str = "development"
    log_level: str = "DEBUG"
    http_port: int = 8000
    base_url: str = ""  # Set in __post_init__
    
    def __post_init__(self):
        if not self.base_url:
            self.base_url = get_base_url()
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"


class ConfigManager:
    """Configuration manager - loads and provides config."""
    
    _instance: Optional["ConfigManager"] = None
    
    def __init__(self):
        self._config: Optional[Config] = None
    
    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def load(self) -> None:
        """Load configuration from environment."""
        env = os.getenv("ENVIRONMENT", "development")
        self._config = Config(
            environment=env,
            log_level=os.getenv("LOG_LEVEL", "DEBUG" if env != "production" else "INFO"),
            http_port=int(os.getenv("MCP_PORT", os.getenv("HTTP_PORT", "8000"))),
            base_url=get_base_url(),
        )
    
    def get(self) -> Config:
        """Get current configuration."""
        if self._config is None:
            # Create default config if not loaded
            self._config = Config()
        return self._config

