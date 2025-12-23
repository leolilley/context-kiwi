"""
Directive Tools
Server-side tools for directive operations.
These are called via the execute() meta-tool.

Available tools:
- get_directive: Fetch directive content from registry
- get_bundle: Fetch multiple directives at once (bundle or list)
- check_updates: Compare local versions against registry
- publish_directive: Publish new directive version to registry

These tools CANNOT touch the user's local files - only Supabase.
The LLM handles local file operations.
"""

from context_kiwi.tools.directives.get import get_directive_handler
from context_kiwi.tools.directives.get_bundle import get_bundle_handler
from context_kiwi.tools.directives.check_updates import check_updates_handler
from context_kiwi.tools.directives.publish import publish_directive_handler
from context_kiwi.tools.directives.delete import delete_directive_handler

__all__ = [
    "get_directive_handler",
    "get_bundle_handler",
    "check_updates_handler",
    "publish_directive_handler",
    "delete_directive_handler",
]
