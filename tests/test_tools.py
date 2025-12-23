"""Tests for the 3 core meta-tools."""

import pytest
from unittest.mock import Mock, AsyncMock
from context_kiwi.tools.core import SearchTool, ExecuteTool, HelpTool
from context_kiwi.mcp_types import ToolInput, ToolContext
from context_kiwi.utils import Logger


@pytest.fixture
def logger():
    return Logger("test", level="ERROR")


@pytest.fixture
def context():
    return ToolContext(
        userId="test",
        requestId="test-req",
        permissions=["execute", "read", "write"],
        accessLevel="read-write",
        timestamp=0.0,
        toolName="test"
    )


class TestSearchTool:
    """Test search_tool."""
    
    @pytest.mark.asyncio
    async def test_requires_query(self, logger, context):
        """Should return error when query is missing."""
        tool = SearchTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, context)
        
        assert not result.success
        assert result.error is not None
        assert "required" in result.error.message.lower()
    
    @pytest.mark.asyncio
    async def test_search_with_valid_query(self, logger, context):
        """Should return results with valid query."""
        tool = SearchTool(logger)
        
        mock_db = Mock()
        mock_db.search.return_value = [
            {
                "name": "test_directive",
                "description": "A test directive",
                "category": "core",
                "latest_version": "1.0.0",
                "download_count": 5,
            }
        ]
        tool._db = mock_db
        
        input_data = ToolInput(query="test")
        result = await tool.execute(input_data, context)
        
        assert result.success
        mock_db.search.assert_called_once()


class TestExecuteTool:
    """Test execute."""
    
    @pytest.mark.asyncio
    async def test_requires_tool_name(self, logger, context):
        """Should return error when tool_name is missing."""
        tool = ExecuteTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, context)
        
        assert not result.success
        assert result.error is not None
        assert "required" in result.error.message.lower()
    
    @pytest.mark.asyncio
    async def test_unknown_tool(self, logger, context):
        """Should return error for unknown directive tool."""
        tool = ExecuteTool(logger)
        input_data = ToolInput(tool_name="unknown_tool")
        
        result = await tool.execute(input_data, context)
        
        assert not result.success
        assert result.error is not None
        assert "not found" in result.error.message.lower()
    
    @pytest.mark.asyncio
    async def test_registered_tool(self, logger, context):
        """Should execute registered directive tool."""
        tool = ExecuteTool(logger)
        
        mock_handler = AsyncMock(return_value={"status": "success", "data": "test"})
        tool.register_directive_tool("test_tool", mock_handler)
        
        input_data = ToolInput(tool_name="test_tool", params={"foo": "bar"})
        result = await tool.execute(input_data, context)
        
        assert result.success
        mock_handler.assert_called_once()


class TestHelpTool:
    """Test help."""
    
    @pytest.mark.asyncio
    async def test_default_topic(self, logger, context):
        """Default topic should return workflow help."""
        tool = HelpTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, context)
        
        assert result.success
        assert result.result is not None
        assert "workflow" in result.result.content[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_tools_topic(self, logger, context):
        """Tools topic should return tools help."""
        tool = HelpTool(logger)
        input_data = ToolInput(topic="tools")
        
        result = await tool.execute(input_data, context)
        
        assert result.success
        assert result.result is not None
        assert "get_directive" in result.result.content[0].text
