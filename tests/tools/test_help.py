"""Tests for HelpTool."""

import pytest
from context_kiwi.tools.help import HelpTool
from context_kiwi.mcp_types import ToolInput


@pytest.mark.asyncio
class TestHelpTool:
    """Test HelpTool."""
    
    async def test_default_topic(self, logger, mock_context):
        """Default topic should return overview help."""
        tool = HelpTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, mock_context)
        
        assert result.success
        assert result.result is not None
        assert result.result.content is not None
    
    async def test_specific_topic(self, logger, mock_context):
        """Should return help for specific topic."""
        tool = HelpTool(logger)
        input_data = ToolInput(topic="search")
        
        result = await tool.execute(input_data, mock_context)
        
        assert result.success
        assert result.result is not None
    
    async def test_unknown_topic(self, logger, mock_context):
        """Should handle unknown topic gracefully."""
        tool = HelpTool(logger)
        input_data = ToolInput(topic="unknown_topic")
        
        result = await tool.execute(input_data, mock_context)
        
        assert result is not None
