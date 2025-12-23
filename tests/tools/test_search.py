"""Tests for SearchTool."""

import pytest
from unittest.mock import Mock, patch
from context_kiwi.tools.search import SearchTool
from context_kiwi.mcp_types import ToolInput
from context_kiwi.directives.loader import DirectiveMatch


@pytest.mark.asyncio
class TestSearchTool:
    """Test SearchTool."""
    
    async def test_requires_query(self, logger, mock_context):
        """Should return error when query is missing."""
        tool = SearchTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
        assert "required" in result.error.message.lower() or "query" in result.error.message.lower()
    
    async def test_search_local_with_valid_query(self, logger, mock_context):
        """Should return results with valid query for local search."""
        tool = SearchTool(logger)
        
        mock_loader = Mock()
        mock_match = DirectiveMatch(
            name="test_directive",
            description="A test directive",
            version="1.0.0",
            source="project",
            score=80.0,
            category="core",
            tech_stack=["Python"]
        )
        mock_loader.search.return_value = [mock_match]
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch('context_kiwi.tools.search.get_tech_stack_list', return_value=[]):
            input_data = ToolInput(query="test", source="local", sort_by="score", project_path="/test/project")
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            assert result.result is not None
            mock_loader.search.assert_called_once()
    
    async def test_search_registry_with_valid_query(self, logger, mock_context):
        """Should return results with valid query for registry search."""
        tool = SearchTool(logger)
        
        mock_loader = Mock()
        mock_match = DirectiveMatch(
            name="test_directive",
            description="A test directive",
            version="1.0.0",
            source="registry",
            score=90.0,
            category="core",
            tech_stack=["Python"],
            quality_score=0.95,
            download_count=5
        )
        mock_loader.search.return_value = [mock_match]
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch('context_kiwi.tools.search.get_tech_stack_list', return_value=["Python"]):
            input_data = ToolInput(query="test", source="registry", sort_by="score")
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            assert result.result is not None
            mock_loader.search.assert_called_once()
    
    async def test_search_all_sources(self, logger, mock_context):
        """Should search both local and registry when source is 'all'."""
        tool = SearchTool(logger)
        
        mock_loader = Mock()
        mock_match1 = DirectiveMatch(
            name="local_directive",
            description="Local",
            version="1.0.0",
            source="project",
            score=80.0,
            category="core"
        )
        mock_match2 = DirectiveMatch(
            name="registry_directive",
            description="Registry",
            version="1.0.0",
            source="registry",
            score=90.0,
            category="core"
        )
        mock_loader.search.return_value = [mock_match1, mock_match2]
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch('context_kiwi.tools.search.get_tech_stack_list', return_value=[]):
            input_data = ToolInput(query="test", source="all", sort_by="score", project_path="/test/project")
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            mock_loader.search.assert_called_once()
    
    async def test_search_with_filters(self, logger, mock_context):
        """Should pass filters to search methods."""
        tool = SearchTool(logger)
        
        mock_loader = Mock()
        mock_loader.search.return_value = []
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch('context_kiwi.tools.search.get_tech_stack_list', return_value=[]):
            input_data = ToolInput(
                query="test",
                source="local",
                sort_by="score",
                project_path="/test/project",
                categories=["patterns"],
                tags=["auth"],
                tech_stack=["React"]
            )
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            call_kwargs = mock_loader.search.call_args[1]
            assert call_kwargs.get("categories") == ["patterns"]
            assert call_kwargs.get("tech_stack_filter") == ["React"]
    
    async def test_search_with_subcategory_filter(self, logger, mock_context):
        """Should pass subcategory filter to search methods."""
        from context_kiwi.directives.loader import DirectiveMatch
        
        tool = SearchTool(logger)
        
        mock_loader = Mock()
        mock_match = DirectiveMatch(
            name="test_api",
            description="Test API directive",
            version="1.0.0",
            source="registry",
            score=90.0,
            category="patterns",
            subcategory="api-endpoints",
            tech_stack=["Python"]
        )
        mock_loader.search.return_value = [mock_match]
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch('context_kiwi.tools.search.get_tech_stack_list', return_value=[]):
            input_data = ToolInput(
                query="test",
                source="registry",
                sort_by="score",
                categories=["patterns"],
                subcategories=["api-endpoints"]
                # Note: project_path not needed for registry search
            )
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            call_kwargs = mock_loader.search.call_args[1]
            assert call_kwargs.get("categories") == ["patterns"]
            assert call_kwargs.get("subcategories") == ["api-endpoints"]
            
            # Verify result includes subcategory
            assert result.result is not None
            # Check that subcategory is in the output

    async def test_search_optional_sort_by(self, logger, mock_context):
        """Should use 'score' as default when sort_by is missing."""
        tool = SearchTool(logger)
        
        mock_loader = Mock()
        mock_loader.search.return_value = []
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch('context_kiwi.tools.search.get_tech_stack_list', return_value=[]):
            # Input data without sort_by but with project_path for local search
            input_data = ToolInput(query="test", source="local", project_path="/test/project")
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            call_kwargs = mock_loader.search.call_args[1]
            assert call_kwargs.get("sort_by") == "score"
    
    async def test_search_local_requires_project_path(self, logger, mock_context):
        """Should return error when searching 'local' without project_path."""
        tool = SearchTool(logger)
        input_data = ToolInput(query="test", source="local")
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
        assert "project_path" in result.error.message.lower()
    
    async def test_search_all_requires_project_path(self, logger, mock_context):
        """Should return error when searching 'all' without project_path."""
        tool = SearchTool(logger)
        input_data = ToolInput(query="test", source="all")
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
        assert "project_path" in result.error.message.lower()
    
    async def test_search_registry_without_project_path(self, logger, mock_context):
        """Should work when searching 'registry' without project_path."""
        tool = SearchTool(logger)
        
        mock_loader = Mock()
        mock_loader.search.return_value = []
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch('context_kiwi.tools.search.get_tech_stack_list', return_value=[]):
            input_data = ToolInput(query="test", source="registry")
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
