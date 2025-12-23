"""Tests for RunTool."""

import pytest
from unittest.mock import Mock, patch
from context_kiwi.tools.run import RunTool
from context_kiwi.mcp_types import ToolInput


@pytest.mark.asyncio
class TestRunTool:
    """Test RunTool."""
    
    async def test_requires_directive(self, logger, mock_context):
        """Should return error when directive is missing."""
        tool = RunTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
        assert "required" in result.error.message.lower() or "directive" in result.error.message.lower()
    
    async def test_unknown_directive(self, logger, mock_context):
        """Should return error for unknown directive."""
        tool = RunTool(logger)
        
        mock_loader = Mock()
        mock_loader.load_local.return_value = None
        
        with patch.object(tool, '_get_loader', return_value=mock_loader):
            input_data = ToolInput(directive="unknown_directive")
            result = await tool.execute(input_data, mock_context)
            
            assert not result.success
            assert result.error is not None
            assert "not found" in result.error.message.lower()
    
    async def test_run_directive_success(self, logger, mock_context):
        """Should successfully run a directive with valid inputs."""
        from context_kiwi.directives.loader import Directive
        
        tool = RunTool(logger)
        
        mock_directive = Directive(
            name="test_directive",
            version="1.0.0",
            description="Test directive",
            content="# Test Directive\n\n<directive name=\"test_directive\">\n<steps>Test steps</steps>\n</directive>",
            parsed={
                "_attrs": {"name": "test_directive", "version": "1.0.0"},
                "steps": {"_text": "Test steps"},
                "inputs": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            },
            source="project",
            tech_stack=["Python"]
        )
        
        mock_loader = Mock()
        mock_loader.load_local.return_value = mock_directive
        
        mock_preflight_result = {
            "pass": True,
            "checks": {},
            "blockers": [],
            "warnings": []
        }
        
        mock_context_data = {
            "tech_stack": "Python",
            "patterns": {}
        }
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch.object(tool, '_run_preflight', return_value=mock_preflight_result), \
             patch('context_kiwi.tools.run.load_context', return_value=mock_context_data), \
             patch('context_kiwi.tools.run.log_run'):
            
            input_data = ToolInput(directive="test_directive", inputs={"name": "test"})
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            assert result.result is not None
    
    async def test_preflight_validation_failure(self, logger, mock_context):
        """Should return error when preflight validation fails."""
        from context_kiwi.directives.loader import Directive
        
        tool = RunTool(logger)
        
        mock_directive = Directive(
            name="test_directive",
            version="1.0.0",
            description="Test",
            content="# Test",
            parsed={
                "_attrs": {"name": "test_directive"},
                "inputs": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"]
                }
            },
            source="project"
        )
        
        mock_loader = Mock()
        mock_loader.load_local.return_value = mock_directive
        
        mock_preflight_result = {
            "pass": False,
            "checks": {},
            "blockers": ["name is required"],
            "warnings": []
        }
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch.object(tool, '_run_preflight', return_value=mock_preflight_result):
            
            input_data = ToolInput(directive="test_directive", inputs={})
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            assert result.result is not None
    
    async def test_credentials_check(self, logger, mock_context):
        """Should check for required credentials."""
        from context_kiwi.directives.loader import Directive
        
        tool = RunTool(logger)
        
        mock_directive = Directive(
            name="test_directive",
            version="1.0.0",
            description="Test",
            content="# Test",
            parsed={
                "_attrs": {"name": "test_directive"},
                "inputs": {"type": "object", "properties": {}},
                "credentials": ["API_KEY"]
            },
            source="project"
        )
        
        mock_loader = Mock()
        mock_loader.load_local.return_value = mock_directive
        
        mock_preflight_result = {
            "pass": False,
            "checks": {
                "credentials": {"status": "fail", "missing": ["API_KEY"]}
            },
            "blockers": ["Missing credentials: API_KEY"],
            "warnings": []
        }
        
        with patch.object(tool, '_get_loader', return_value=mock_loader), \
             patch.object(tool, '_run_preflight', return_value=mock_preflight_result):
            
            input_data = ToolInput(directive="test_directive", inputs={})
            result = await tool.execute(input_data, mock_context)
            
            assert result.success
            result_data = result.result.content[0].text if result.result else ""
            assert "credential" in result_data.lower() or "api_key" in result_data.lower()
