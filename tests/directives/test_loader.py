"""Tests for DirectiveLoader."""

from unittest.mock import Mock, patch
from context_kiwi.directives.loader import DirectiveLoader


class TestDirectiveLoader:
    """Test DirectiveLoader."""
    
    def test_load_directive_from_project(self, tmp_path):
        """Should load directive from project space."""
        ai_path = tmp_path / ".ai" / "directives" / "custom"
        ai_path.mkdir(parents=True)
        
        directive_file = ai_path / "test_directive.md"
        directive_file.write_text("""# Test Directive

<directive name="test_directive" version="1.0.0">
<metadata>
<description>Test directive</description>
</metadata>
<steps>Test steps</steps>
</directive>""")
        
        loader = DirectiveLoader(project_path=tmp_path)
        directive = loader.load("test_directive")
        
        assert directive is not None
        assert directive.name == "test_directive"
    
    def test_load_directive_from_user_space(self, tmp_path):
        """Should load directive from user space when not in project."""
        user_path = tmp_path / "user" / "directives" / "core"
        user_path.mkdir(parents=True)
        
        directive_file = user_path / "test_directive.md"
        directive_file.write_text("""# Test Directive

<directive name="test_directive" version="1.0.0">
<metadata>
<description>Test directive</description>
</metadata>
<steps>Test steps</steps>
</directive>""")
        
        with patch('context_kiwi.config.get_user_home', return_value=tmp_path / "user"):
            loader = DirectiveLoader(project_path=tmp_path)
            directive = loader.load("test_directive")
            
            assert directive is not None
    
    def test_load_directive_not_found(self, tmp_path):
        """Should return None when directive not found."""
        loader = DirectiveLoader(project_path=tmp_path)
        directive = loader.load("nonexistent")
        
        assert directive is None
    
    def test_search_local(self, tmp_path):
        """Should search for directives in local space."""
        ai_path = tmp_path / ".ai" / "directives" / "custom"
        ai_path.mkdir(parents=True)
        
        directive_file = ai_path / "test_directive.md"
        directive_file.write_text("""# Test Directive

<directive name="test_directive">
<metadata>
<description>Test directive description</description>
</metadata>
</directive>""")
        
        loader = DirectiveLoader(project_path=tmp_path)
        results = loader.search(query="test", source="local", sort_by="score")
        
        assert len(results) > 0
        assert any(r.name == "test_directive" for r in results)
    
    def test_search_registry(self, mock_supabase):
        """Should search registry for directives."""
        loader = DirectiveLoader()
        
        mock_db = Mock()
        mock_db.is_available = True
        mock_db.search.return_value = [
            {
                "name": "test_directive",
                "description": "Test directive",
                "category": "core",
                "subcategory": None,
                "latest_version": "1.0.0",
                "tech_stack": [],
                "quality_score": 0.9,
                "download_count": 5,
                "compatibility_score": 0.95
            }
        ]
        
        with patch('context_kiwi.db.directives.DirectiveDB', return_value=mock_db):
            results = loader.search(query="test", source="registry", sort_by="score")
            
            assert isinstance(results, list)
            assert len(results) > 0
            assert results[0].name == "test_directive"
    
    def test_extract_subcategory_from_xml(self, tmp_path):
        """Should extract subcategory from directive XML content."""
        ai_path = tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints"
        ai_path.mkdir(parents=True)
        
        directive_file = ai_path / "test_api.md"
        directive_file.write_text("""# Test API

<directive name="test_api" version="1.0.0">
<metadata>
<description>Test API directive</description>
<category>patterns</category>
<subcategory>api-endpoints</subcategory>
</metadata>
<steps>Test steps</steps>
</directive>""")
        
        loader = DirectiveLoader(project_path=tmp_path)
        results = loader.search(query="test", source="local", sort_by="score")
        
        assert len(results) > 0
        api_result = next((r for r in results if r.name == "test_api"), None)
        assert api_result is not None
        assert api_result.subcategory == "api-endpoints"
        assert api_result.category == "patterns"
    
    def test_extract_subcategory_from_path(self, tmp_path):
        """Should extract subcategory from file path when not in XML."""
        ai_path = tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints"
        ai_path.mkdir(parents=True)
        
        directive_file = ai_path / "test_api.md"
        directive_file.write_text("""# Test API

<directive name="test_api" version="1.0.0">
<metadata>
<description>Test API directive</description>
<category>patterns</category>
</metadata>
<steps>Test steps</steps>
</directive>""")
        
        loader = DirectiveLoader(project_path=tmp_path)
        results = loader.search(query="test", source="local", sort_by="score")
        
        assert len(results) > 0
        api_result = next((r for r in results if r.name == "test_api"), None)
        assert api_result is not None
        # Should extract subcategory from path: patterns/api-endpoints/
        assert api_result.subcategory == "api-endpoints"
        assert api_result.category == "patterns"
    
    def test_search_with_subcategory_filter_local(self, tmp_path):
        """Should filter local search results by subcategory."""
        # Create directives in different subcategories
        patterns_api = tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints"
        patterns_api.mkdir(parents=True)
        (patterns_api / "test_api.md").write_text("""# Test API
<directive name="test_api" version="1.0.0">
<metadata><category>patterns</category><subcategory>api-endpoints</subcategory></metadata>
</directive>""")
        
        patterns_ui = tmp_path / ".ai" / "directives" / "patterns" / "ui-components"
        patterns_ui.mkdir(parents=True)
        (patterns_ui / "test_ui.md").write_text("""# Test UI
<directive name="test_ui" version="1.0.0">
<metadata><category>patterns</category><subcategory>ui-components</subcategory></metadata>
</directive>""")
        
        loader = DirectiveLoader(project_path=tmp_path)
        results = loader.search(
            query="test",
            source="local",
            sort_by="score",
            subcategories=["api-endpoints"]
        )
        
        # Should only return api-endpoints directive
        assert len(results) > 0
        assert all(r.subcategory == "api-endpoints" for r in results)
        assert not any(r.subcategory == "ui-components" for r in results)
    
    def test_search_with_subcategory_filter_registry(self, mock_supabase):
        """Should filter registry search results by subcategory."""
        loader = DirectiveLoader()
        
        mock_db = Mock()
        mock_db.is_available = True
        mock_db.search.return_value = [
            {
                "name": "test_api",
                "description": "Test API directive",
                "category": "patterns",
                "subcategory": "api-endpoints",
                "latest_version": "1.0.0",
                "tech_stack": [],
                "quality_score": 0.9,
                "download_count": 5,
                "compatibility_score": 0.95
            }
        ]
        
        with patch('context_kiwi.db.directives.DirectiveDB', return_value=mock_db):
            results = loader.search(
                query="test",
                source="registry",
                sort_by="score",
                subcategories=["api-endpoints"]
            )
            
            assert isinstance(results, list)
            assert len(results) > 0
            assert results[0].name == "test_api"
            assert results[0].subcategory == "api-endpoints"
            # Verify subcategories filter was passed to db.search
            mock_db.search.assert_called_once()
            call_kwargs = mock_db.search.call_args[1]
            assert call_kwargs.get("subcategories") == ["api-endpoints"]
