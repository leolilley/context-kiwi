"""Analytics and run logging database operations."""

from typing import Any, Dict, Optional

from context_kiwi.db.client import get_supabase_client, SupabaseClient
from context_kiwi.utils.logger import Logger


class AnalyticsDB:
    """Database operations for run analytics."""
    
    def __init__(self, client: Optional[SupabaseClient] = None, logger: Optional[Logger] = None):
        self._client = client
        self.logger = logger or Logger("analytics-db")
    
    @property
    def client(self) -> SupabaseClient:
        if self._client is None:
            self._client = get_supabase_client()
        return self._client
    
    def log_run(
        self,
        directive_name: str,
        status: str,
        directive_version: Optional[str] = None,
        duration_sec: Optional[float] = None,
        cost_usd: Optional[float] = None,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log a directive run for analytics."""
        try:
            self.client.table("runs").insert({
                "directive_name": directive_name,
                "directive_version": directive_version,
                "status": status,
                "duration_sec": duration_sec,
                "cost_usd": cost_usd,
                "inputs": inputs,
                "outputs": outputs,
                "error": error,
                "project_context": project_context,
            }).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to log run for {directive_name}: {e}")
            return False

