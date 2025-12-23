"""
Execution Module

Pre-flight validation, context loading, and run analytics.
"""

from .analytics import (
    log_run,
    get_run_history,
    directive_stats,
    identify_anneal_candidates,
    recent_failures,
)

from .preflight import (
    run_preflight,
    check_credentials,
    validate_inputs,
    validate_inputs_simple,
)

from .context import (
    load_context,
    get_tech_stack_list,
    has_context,
    get_context_summary,
)

__all__ = [
    # Analytics
    "log_run",
    "get_run_history",
    "directive_stats",
    "identify_anneal_candidates",
    "recent_failures",
    # Preflight
    "run_preflight",
    "check_credentials",
    "validate_inputs",
    "validate_inputs_simple",
    # Context
    "load_context",
    "get_tech_stack_list",
    "has_context",
    "get_context_summary",
]
