"""Tests for Supabase client."""

from unittest.mock import patch
from context_kiwi.db.client import SupabaseClient


class TestSupabaseClient:
    """Test SupabaseClient."""
    
    def test_is_configured_true(self):
        """Should return True when configured."""
        with patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_SECRET_KEY': 'test-key'}):
            client = SupabaseClient()
            assert client.is_configured is True
    
    def test_is_configured_false(self):
        """Should return False when not configured."""
        with patch.dict('os.environ', {}, clear=True):
            client = SupabaseClient()
            assert client.is_configured is False
    
    def test_table_access(self, mock_supabase):
        """Should access table through client."""
        with patch('context_kiwi.db.client.SupabaseClient.get_instance', return_value=mock_supabase):
            client = SupabaseClient.get_instance()
            table = client.table('directives')
            
            assert table is not None
    
    def test_singleton_instance(self):
        """Should return same instance on multiple calls."""
        with patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_SECRET_KEY': 'test-key'}):
            instance1 = SupabaseClient.get_instance()
            instance2 = SupabaseClient.get_instance()
            
            assert instance1 is instance2
