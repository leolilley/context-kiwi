"""
Registry Module
Pattern and directive registry, search, and serving.

NOTE: Directive discovery goes through MCP tools (search_directive).
This module only serves files for LLM to download during bootstrap.
"""

from .download import serve_directive

__all__ = ["serve_directive"]

