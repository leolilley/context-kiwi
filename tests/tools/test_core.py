"""Tests for core tools (legacy SearchTool, ExecuteTool, HelpTool)."""

import pytest
from unittest.mock import AsyncMock
from context_kiwi.tools.core import SearchTool, ExecuteTool, HelpTool
from context_kiwi.mcp_types import ToolInput


@pytest.mark.asyncio
class TestLegacySearchTool:
    """Test legacy SearchTool (if still exists)."""
    
    async def test_requires_query(self, logger, mock_context):
        """Should return error when query is missing."""
        tool = SearchTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None


@pytest.mark.asyncio
class TestLegacyExecuteTool:
    """Test legacy ExecuteTool (if still exists)."""
    
    async def test_requires_tool_name(self, logger, mock_context):
        """Should return error when tool_name is missing."""
        tool = ExecuteTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
    
    async def test_unknown_tool(self, logger, mock_context):
        """Should return error for unknown directive tool."""
        tool = ExecuteTool(logger)
        input_data = ToolInput(tool_name="unknown_tool")
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
        assert "not found" in result.error.message.lower()
    
    async def test_registered_tool(self, logger, mock_context):
        """Should execute registered directive tool."""
        tool = ExecuteTool(logger)
        
        mock_handler = AsyncMock(return_value={"status": "success", "data": "test"})
        tool.register_directive_tool("test_tool", mock_handler)
        
        input_data = ToolInput(tool_name="test_tool", params={"foo": "bar"})
        result = await tool.execute(input_data, mock_context)
        
        assert result.success
        mock_handler.assert_called_once()


@pytest.mark.asyncio
class TestLegacyHelpTool:
    """Test legacy HelpTool (if still exists)."""
    
    async def test_default_topic(self, logger, mock_context):
        """Default topic should return workflow help."""
        tool = HelpTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, mock_context)
        
        assert result.success
        assert result.result is not None
