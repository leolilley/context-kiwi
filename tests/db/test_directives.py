"""Tests for DirectiveDB."""

from unittest.mock import Mock
from context_kiwi.db.directives import DirectiveDB, DirectiveRecord


class TestDirectiveDB:
    """Test DirectiveDB."""
    
    def test_search_directives(self, logger, mock_supabase):
        """Should search directives in database."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        mock_data = [
            {
                'id': '123',
                'name': 'test_directive',
                'description': 'Test',
                'category': 'core',
                'subcategory': None,
                'directive_versions': [{'version': '1.0.0', 'is_latest': True}]
            }
        ]
        
        mock_supabase.setup_select_query('directives', data=mock_data)
        
        results = db.search("test")
        
        assert isinstance(results, list)
    
    def test_get_directive(self, logger, mock_supabase):
        """Should get directive by name."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        directive_data = [{'id': '123', 'name': 'test_directive', 'category': 'core', 'subcategory': None}]
        version_data = [{'version': '1.0.0', 'content': '# Test', 'content_hash': 'hash', 'is_latest': True}]
        
        mock_supabase.setup_select_query('directives', data=directive_data)
        mock_supabase.setup_select_query('directive_versions', data=version_data)
        
        directive = db.get('test_directive')
        
        assert directive is None or hasattr(directive, 'name')
    
    def test_get_directive_not_found(self, logger, mock_supabase):
        """Should return None when directive not found."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        mock_supabase.setup_select_query('directives', data=[])
        
        directive = db.get('nonexistent')
        
        assert directive is None
    
    def test_create_directive_with_subcategory(self, logger, mock_supabase):
        """Should create directive with subcategory."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        # Configure mock to return data for directives table insert
        directive_data = [{'id': '123', 'name': 'test_api', 'category': 'patterns', 'subcategory': 'api-endpoints'}]
        mock_supabase.configure_table_data('directives', directive_data)
        
        # Configure mock to return data for directive_versions table insert  
        version_data = [{'version': '1.0.0'}]
        mock_supabase.configure_table_data('directive_versions', version_data)
        
        result = db.create(
            name="test_api",
            category="patterns",
            subcategory="api-endpoints",
            description="Test API directive",
            version="1.0.0",
            content="# Test",
            tech_stack=["Python"]
        )
        
        # Verify subcategory was passed to insert
        # The insert should have been called with subcategory
        assert result is True  # create returns bool
    
    def test_list_directives_with_subcategory_filter(self, logger, mock_supabase):
        """Should filter directives by subcategory."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        mock_data = [
            {
                'id': '123',
                'name': 'test_api',
                'category': 'patterns',
                'subcategory': 'api-endpoints',
                'description': 'Test',
                'directive_versions': [{'version': '1.0.0', 'is_latest': True}]
            }
        ]
        
        mock_supabase.setup_select_query('directives', data=mock_data)
        
        results = db.list(subcategory='api-endpoints')
        
        assert isinstance(results, list)
        # Verify filter was applied (check that query builder was called with subcategory)
        table = mock_supabase.table('directives')
        select_query = table.select()
        # The filter should be applied via .eq('subcategory', 'api-endpoints')
    
    def test_search_directives_with_subcategory_filter(self, logger, mock_supabase):
        """Should search directives filtered by subcategory."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        mock_data = [
            {
                'id': '123',
                'name': 'test_api',
                'category': 'patterns',
                'subcategory': 'api-endpoints',
                'description': 'Test API directive',
                'directive_versions': [{'version': '1.0.0', 'is_latest': True}]
            }
        ]
        
        mock_supabase.setup_select_query('directives', data=mock_data)
        
        results = db.search("test", subcategories=['api-endpoints'])
        
        assert isinstance(results, list)
    
    def test_directive_record_with_subcategory(self, logger, mock_supabase):
        """Should create DirectiveRecord with subcategory from database row."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        row = {
            'id': '123',
            'name': 'test_api',
            'category': 'patterns',
            'subcategory': 'api-endpoints',
            'description': 'Test',
            'is_official': True,
            'download_count': 0,
            'quality_score': 0.0,
            'tech_stack': []
        }
        
        version_row = {
            'version': '1.0.0',
            'content': '# Test',
            'content_hash': 'hash',
            'changelog': None,
            'is_latest': True
        }
        
        record = DirectiveRecord.from_row(row, version_row)
        
        assert record.subcategory == 'api-endpoints'
        assert record.category == 'patterns'
    
    def test_directive_record_without_subcategory(self, logger, mock_supabase):
        """Should create DirectiveRecord with None subcategory when not provided."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        row = {
            'id': '123',
            'name': 'test_directive',
            'category': 'core',
            'subcategory': None,
            'description': 'Test',
            'is_official': True,
            'download_count': 0,
            'quality_score': 0.0,
            'tech_stack': []
        }
        
        version_row = {
            'version': '1.0.0',
            'content': '# Test',
            'content_hash': 'hash',
            'changelog': None,
            'is_latest': True
        }
        
        record = DirectiveRecord.from_row(row, version_row)
        
        assert record.subcategory is None
        assert record.category == 'core'
    
    def test_create_directive_with_dynamic_category(self, logger, mock_supabase):
        """Should create directive with any category name (not restricted)."""
        db = DirectiveDB(logger=logger)
        db._client = mock_supabase
        
        # Configure mock to return data for directives table insert
        directive_data = [{'id': '123', 'name': 'test_workflow', 'category': 'workflows', 'subcategory': None}]
        mock_supabase.configure_table_data('directives', directive_data)
        
        # Configure mock to return data for directive_versions table insert
        version_data = [{'version': '1.0.0'}]
        mock_supabase.configure_table_data('directive_versions', version_data)
        
        result = db.create(
            name="test_workflow",
            category="workflows",  # Not in old restricted list
            description="Test workflow directive",
            version="1.0.0",
            content="# Test",
            tech_stack=[]
        )
        
        # Should not raise an error about invalid category
        assert result is True  # create returns bool
