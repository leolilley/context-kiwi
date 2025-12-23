"""
Shared pytest fixtures for Context Kiwi MCP tests

Centralized mocking infrastructure to eliminate duplication across test files.
Provides reusable fixtures and helper classes for mocking Supabase, config, and other dependencies.
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from typing import Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# ============================================================================
# Mock Helper Classes
# ============================================================================

class SupabaseQueryBuilder:
    """
    Builder pattern for creating Supabase query mocks.
    
    Creates a fluent query chain that supports methods like:
    .select().eq().in_().limit().execute().data
    
    Usage:
        builder = SupabaseQueryBuilder([{'id': '123'}])
        query = builder.build()
        result = query.select().eq('id', '123').execute()
        assert result.data == [{'id': '123'}]
    """
    
    def __init__(self, data: Any = None):
        """
        Initialize query builder with optional default data.
        
        Args:
            data: Default data to return when execute() is called.
                  Can be a list, dict, or None. Defaults to [].
        """
        self.data = data if data is not None else []
        self._count = None
        self._query = Mock()
        self._setup_chain()
    
    def _setup_chain(self):
        """Setup the fluent query chain - all methods return self to allow chaining."""
        self._is_single = False
        self._is_maybe_single = False
        
        self._query.eq = Mock(return_value=self._query)
        self._query.in_ = Mock(return_value=self._query)
        self._query.limit = Mock(return_value=self._query)
        self._query.offset = Mock(return_value=self._query)
        self._query.order = Mock(return_value=self._query)
        self._query.gte = Mock(return_value=self._query)
        self._query.lte = Mock(return_value=self._query)
        self._query.gt = Mock(return_value=self._query)
        self._query.lt = Mock(return_value=self._query)
        
        not_mock = Mock()
        not_mock.is_ = Mock(return_value=self._query)
        self._query.not_ = not_mock
        
        def single_side_effect():
            self._is_single = True
            return self._query
        self._query.single = Mock(side_effect=single_side_effect)
        
        def maybe_single_side_effect():
            self._is_maybe_single = True
            return self._query
        self._query.maybe_single = Mock(side_effect=maybe_single_side_effect)
        
        self._query.insert = Mock(return_value=self._query)
        self._query.update = Mock(return_value=self._query)
        self._query.upsert = Mock(return_value=self._query)
        self._query.delete = Mock(return_value=self._query)
        
        def select_side_effect(*args, **kwargs):
            if 'count' in kwargs:
                self._count = kwargs['count']
            return self._query
        self._query.select = Mock(side_effect=select_side_effect)
        
        def execute_side_effect():
            mock_response = Mock()
            if self._is_single or self._is_maybe_single:
                if isinstance(self.data, list) and len(self.data) > 0:
                    mock_response.data = self.data[0]
                elif isinstance(self.data, dict):
                    mock_response.data = self.data
                else:
                    mock_response.data = self.data
            else:
                if isinstance(self.data, dict):
                    mock_response.data = [self.data]
                else:
                    mock_response.data = self.data if self.data is not None else []
            
            if self._count == 'exact':
                if isinstance(mock_response.data, list):
                    count_value = len(mock_response.data)
                else:
                    count_value = 1 if mock_response.data else 0
                mock_response.count = count_value
            else:
                if hasattr(mock_response, 'count'):
                    delattr(mock_response, 'count')
            
            return mock_response
        
        self._query.execute = Mock(side_effect=execute_side_effect)
    
    def build(self):
        """Return the configured query mock."""
        return self._query


class SupabaseTableMock:
    """
    Mock for a Supabase table with query builder support.
    
    Provides select(), insert(), update(), delete() methods that return
    query builders configured with default data.
    
    Usage:
        table = SupabaseTableMock([{'id': '123'}])
        query = table.select()
        result = query.eq('id', '123').execute()
        assert result.data == [{'id': '123'}]
    """
    
    def __init__(self, default_data: Any = None):
        """
        Initialize table mock with optional default data.
        
        Args:
            default_data: Default data returned by queries. Defaults to [].
        """
        self.default_data = default_data if default_data is not None else []
    
    def select(self, *args, **kwargs):
        """Mock select() - returns a query builder with current default_data."""
        builder = SupabaseQueryBuilder(self.default_data)
        if 'count' in kwargs:
            builder._count = kwargs['count']
        query = builder.build()
        return query
    
    def insert(self, *args, **kwargs):
        """Mock insert() - returns a query builder that returns inserted data."""
        # If data was provided in args, use it; otherwise use default_data
        if args and isinstance(args[0], dict):
            # Single insert - wrap in list
            inserted_data = [args[0].copy()]
            # Add id if not present
            if 'id' not in inserted_data[0]:
                inserted_data[0]['id'] = 'mock-id-123'
        elif args and isinstance(args[0], list):
            # Bulk insert
            inserted_data = args[0]
        else:
            # Use default_data or empty list
            inserted_data = self.default_data if isinstance(self.default_data, list) else [self.default_data] if self.default_data else []
        
        builder = SupabaseQueryBuilder(inserted_data)
        return builder.build()
    
    def update(self, *args, **kwargs):
        """Mock update() - returns a query builder that can modify table data."""
        builder = SupabaseQueryBuilder()
        query = builder.build()
        
        original_execute = query.execute
        def update_execute_side_effect():
            result = original_execute()
            result.data = []
            return result
        
        query.execute = Mock(side_effect=update_execute_side_effect)
        return query
    
    def upsert(self, *args, **kwargs):
        """Mock upsert() - returns a query builder."""
        builder = SupabaseQueryBuilder()
        return builder.build()
    
    def delete(self, *args, **kwargs):
        """Mock delete() - returns a query builder."""
        builder = SupabaseQueryBuilder()
        return builder.build()


class MockSupabaseClient:
    """
    Centralized Supabase client mock with all common tables pre-configured.
    
    Provides a complete mock of SupabaseClient with:
    - All common tables pre-configured with sensible defaults
    - table() method for direct table access
    - RPC support
    
    Usage:
        mock_supabase = MockSupabaseClient()
        mock_supabase.configure_table_data('directives', [{'id': '123'}])
        table = mock_supabase.table('directives')
    """
    
    def __init__(self):
        """Initialize mock Supabase client with all common tables."""
        self._tables = {
            'directives': SupabaseTableMock(),
            'directive_versions': SupabaseTableMock(),
            'directive_runs': SupabaseTableMock(),
            'directive_analytics': SupabaseTableMock(),
        }
        
        self.is_configured = True
        
        def table_side_effect(table_name: str):
            if table_name in self._tables:
                return self._tables[table_name]
            new_table = SupabaseTableMock()
            self._tables[table_name] = new_table
            return new_table
        
        self.table = Mock(side_effect=table_side_effect)
        self.rpc = Mock(return_value=SupabaseQueryBuilder().build())
        self.client = self
    
    def configure_table_data(self, table_name: str, data: Any):
        """
        Configure default data for a table.
        
        Args:
            table_name: Name of the table to configure
            data: Default data to return (list, dict, or None)
        
        Usage:
            mock_supabase.configure_table_data('directives', [{'id': '123'}])
        """
        if table_name in self._tables:
            self._tables[table_name].default_data = data
        else:
            self._tables[table_name] = SupabaseTableMock(data)
    
    def setup_select_query(self, table_name: str, filters: Optional[Dict[str, Any]] = None, 
                          data: Any = None, single: bool = False, maybe_single: bool = False):
        """
        Setup a select query with filters and return data.
        
        Args:
            table_name: Name of the table
            filters: Dictionary of filters to apply
            data: Data to return (list for multiple, dict for single). If None, uses table's default_data
            single: If True, chain .single() before execute()
            maybe_single: If True, chain .maybe_single() before execute()
        
        Returns:
            Configured query builder mock
        """
        table = self.table(table_name)
        
        if data is None:
            return_data = table.default_data
        else:
            return_data = data
        
        builder = SupabaseQueryBuilder(return_data)
        query = builder.build()
        
        table.select = Mock(return_value=query)
        
        return query


# ============================================================================
# Base Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """
    Standard mock configuration for all tests.
    
    Provides all required Config attributes with sensible defaults.
    """
    from context_kiwi.config.settings import Config
    
    config = Mock(spec=Config)
    config.environment = "test"
    config.log_level = "DEBUG"
    config.http_port = 8000
    config.base_url = "http://localhost:8000"
    config.is_production = False
    config.is_development = True
    return config


@pytest.fixture
def logger():
    """
    Standard mock logger for all tests.
    """
    from context_kiwi.utils.logger import Logger
    return Mock(spec=Logger)


@pytest.fixture
def mock_supabase():
    """
    Standard Supabase client mock.
    
    Returns a MockSupabaseClient instance with all common tables pre-configured.
    Use configure_table_data() to set test-specific data.
    
    Usage:
        def test_something(mock_supabase):
            mock_supabase.configure_table_data('directives', [{'id': '123'}])
            # ... test code
    """
    return MockSupabaseClient()


@pytest.fixture
def mock_context():
    """
    Standard mock ToolContext for all tests.
    """
    from context_kiwi.mcp_types.tools import ToolContext
    
    return ToolContext(
        userId='test_user',
        requestId='test_req_123',
        permissions=['execute', 'read', 'write'],
        accessLevel='read-write',
        timestamp=1234567890.0,
        toolName=None
    )


@pytest.fixture
def supabase_patch(mock_supabase):
    """
    Context manager for patching get_supabase_client across all modules.
    
    Usage:
        def test_something(supabase_patch):
            with supabase_patch as mock_supabase:
                mock_supabase.configure_table_data('directives', [{'id': '123'}])
    """
    from contextlib import contextmanager
    
    @contextmanager
    def _patch():
        with pytest.MonkeyPatch().context() as m:
            m.setattr('context_kiwi.db.client.SupabaseClient.get_instance', lambda: mock_supabase)
            m.setattr('context_kiwi.db.directives.SupabaseClient.get_instance', lambda: mock_supabase)
            yield mock_supabase
    
    return _patch
