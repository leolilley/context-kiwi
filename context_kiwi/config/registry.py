"""
Registry Configuration

Centralized configuration for Context Kiwi.
"""

import os
from pathlib import Path


def get_user_home() -> Path:
    """Get Context Kiwi user home directory.
    
    Uses CONTEXT_KIWI_HOME env var if set, otherwise ~/.context-kiwi/
    """
    env_home = os.environ.get("CONTEXT_KIWI_HOME")
    if env_home:
        # Expand ~ to actual home directory if present
        expanded = os.path.expanduser(env_home)
        return Path(expanded)
    return Path.home() / ".context-kiwi"


def get_supabase_url() -> str:
    """Get the Supabase URL from environment.
    
    Raises ValueError if not set.
    """
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ValueError(
            "SUPABASE_URL environment variable is required. "
            "Please set it to your Supabase project URL (e.g., https://your-project.supabase.co)"
        )
    return url


def get_supabase_anon_key() -> str:
    """Get the Supabase anon key (public, for read access) from environment.
    
    Raises ValueError if not set.
    """
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not key:
        raise ValueError(
            "SUPABASE_ANON_KEY environment variable is required. "
            "You can find this in your Supabase project settings."
        )
    return key


def get_supabase_key() -> str:
    """Get the Supabase key - secret if available, else anon."""
    secret = os.environ.get("SUPABASE_SECRET_KEY")
    if secret:
        return secret
    return get_supabase_anon_key()


def get_supabase_headers() -> dict:
    """Get headers for Supabase REST API calls."""
    key = get_supabase_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

