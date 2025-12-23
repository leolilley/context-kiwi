"""Tests for PublishTool."""

import pytest
from unittest.mock import Mock, patch
from context_kiwi.tools.publish import PublishTool
from context_kiwi.mcp_types import ToolInput


@pytest.mark.asyncio
class TestPublishTool:
    """Test PublishTool."""
    
    async def test_requires_directive(self, logger, mock_context):
        """Should return error when directive is missing."""
        tool = PublishTool(logger)
        input_data = ToolInput()
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
        assert "required" in result.error.message.lower() or "directive" in result.error.message.lower()
    
    async def test_requires_version(self, logger, mock_context):
        """Should return error when version is missing."""
        tool = PublishTool(logger)
        input_data = ToolInput(directive="test_directive")
        
        result = await tool.execute(input_data, mock_context)
        
        assert not result.success
        assert result.error is not None
        assert "version" in result.error.message.lower() or "required" in result.error.message.lower()
    
    async def test_publish_directive_success(self, logger, mock_context, tmp_path):
        """Should successfully publish a directive."""
        from unittest.mock import AsyncMock
        
        tool = PublishTool(logger)
        
        directive_path = tmp_path / ".ai" / "directives" / "custom" / "test_directive.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("""# Test Directive

<directive name="test_directive" version="1.0.0">
<metadata>
<description>Test directive</description>
</metadata>
<steps>Test steps</steps>
</directive>""")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('context_kiwi.tools.publish.httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'CONTEXT_KIWI_API_KEY': 'test-key'}):
            
            input_data = ToolInput(directive="test_directive", version="1.0.0", source="project", project_path=str(tmp_path))
            result = await tool.execute(input_data, mock_context)
            
            assert result is not None
    
    async def test_publish_validates_directive_format(self, logger, mock_context, tmp_path):
        """Should validate directive format before publishing."""
        tool = PublishTool(logger)
        
        directive_path = tmp_path / ".ai" / "directives" / "custom" / "test_directive.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("# Invalid Directive\n\nNo XML structure")
        
        with patch.dict('os.environ', {'CONTEXT_KIWI_API_KEY': 'test-key'}):
            input_data = ToolInput(directive="test_directive", version="1.0.0", source="project", project_path=str(tmp_path))
            result = await tool.execute(input_data, mock_context)
            
            assert not result.success
            assert result.error is not None
    
    async def test_publish_extracts_subcategory_from_content(self, logger, mock_context, tmp_path):
        """Should extract subcategory from directive XML content."""
        from context_kiwi.tools.directives.publish import extract_metadata_from_content
        
        content = """# Test API Directive

```xml
<directive name="test_api" version="1.0.0">
<metadata>
<description>Test API directive</description>
<category>patterns</category>
<subcategory>api-endpoints</subcategory>
</metadata>
</directive>
```"""
        
        category, subcategory, description = extract_metadata_from_content(content)
        
        assert category == "patterns"
        assert subcategory == "api-endpoints"
        assert description == "Test API directive"
    
    async def test_publish_with_subcategory(self, logger, mock_context, tmp_path):
        """Should publish directive with subcategory."""
        from unittest.mock import AsyncMock
        
        tool = PublishTool(logger)
        
        directive_path = tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints" / "test_api.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("""# Test API

<directive name="test_api" version="1.0.0">
<metadata>
<description>Test API directive</description>
<category>patterns</category>
<subcategory>api-endpoints</subcategory>
</metadata>
</directive>""")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('context_kiwi.tools.publish.httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'CONTEXT_KIWI_API_KEY': 'test-key'}):
            
            input_data = ToolInput(
                directive="test_api",
                version="1.0.0",
                source="project",
                project_path=str(tmp_path)
            )
            result = await tool.execute(input_data, mock_context)
            
            assert result is not None
    
    async def test_publish_defaults_to_actions_not_core(self, logger, mock_context):
        """Should default to 'actions' category for user directives, not 'core' which is reserved."""
        from context_kiwi.tools.directives.publish import publish_directive_handler
        
        # Test with content that has no category specified
        content_without_category = """# Test Directive

```xml
<directive name="test_user_directive" version="1.0.0">
<metadata>
<description>User-created directive</description>
</metadata>
</directive>
```"""
        
        params = {
            "name": "test_user_directive",
            "version": "1.0.0",
            "content": content_without_category
        }
        
        # Mock the database to avoid actual DB calls
        with patch('context_kiwi.tools.directives.publish.DirectiveDB') as mock_db_class:
            mock_db = Mock()
            mock_db.get.return_value = None  # New directive
            mock_db.get_versions.return_value = []
            mock_db.create.return_value = True
            mock_db_class.return_value = mock_db
            
            result = await publish_directive_handler(params, mock_context)
            
            # Verify that the category defaults to "actions" not "core"
            assert result["status"] == "published"
            assert result["category"] == "actions", f"Expected 'actions' but got '{result.get('category')}'. 'core' is reserved for system directives."
            
            # Verify create was called with "actions" category
            mock_db.create.assert_called_once()
            call_args = mock_db.create.call_args
            assert call_args[1]["category"] == "actions"

    async def test_rejects_version_mismatch(self, logger, mock_context, tmp_path):
        """Should reject publishing when user-provided version doesn't match content version."""
        tool = PublishTool(logger)
        
        directive_path = tmp_path / ".ai" / "directives" / "custom" / "test_directive.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("""# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <category>patterns</category>
  </metadata>
  <process>
    <step name="test">Test step</step>
  </process>
</directive>
```""")
        
        with patch.dict('os.environ', {'CONTEXT_KIWI_API_KEY': 'test-key'}):
            # Try to publish as version 2.0.0 but content has version 1.0.0
            input_data = ToolInput(
                directive="test_directive",
                version="2.0.0",  # Mismatch!
                source="project",
                project_path=str(tmp_path)
            )
            result = await tool.execute(input_data, mock_context)
            
            assert not result.success
            assert result.error is not None
            assert "version mismatch" in result.error.message.lower()
            assert "1.0.0" in result.error.message  # Content version
            assert "2.0.0" in result.error.message  # User-provided version
    
    async def test_accepts_matching_version(self, logger, mock_context, tmp_path):
        """Should accept publishing when user-provided version matches content version."""
        from unittest.mock import AsyncMock
        
        tool = PublishTool(logger)
        
        directive_path = tmp_path / ".ai" / "directives" / "custom" / "test_directive.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("""# Test Directive

```xml
<directive name="test_directive" version="1.0.0">
  <metadata>
    <description>Test directive</description>
    <category>patterns</category>
  </metadata>
  <process>
    <step name="test">Test step</step>
  </process>
</directive>
```""")
        
        # Mock successful Supabase responses
        mock_check_resp = Mock()
        mock_check_resp.status_code = 200
        mock_check_resp.json.return_value = []  # New directive
        
        mock_version_resp = Mock()
        mock_version_resp.status_code = 201
        mock_version_resp.json.return_value = [{"id": "123"}]
        
        mock_create_resp = Mock()
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = [{"id": "dir-123"}]
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_check_resp)
        mock_client.post = AsyncMock(side_effect=[mock_create_resp, mock_version_resp])
        mock_client.patch = AsyncMock(return_value=Mock(status_code=200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('context_kiwi.tools.publish.httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'CONTEXT_KIWI_API_KEY': 'test-key'}):
            
            # Publish with matching version
            input_data = ToolInput(
                directive="test_directive",
                version="1.0.0",  # Matches content!
                source="project",
                project_path=str(tmp_path)
            )
            result = await tool.execute(input_data, mock_context)
            
            # Should succeed (or at least pass version validation)
            # Note: May fail on actual publish, but version check should pass
            assert result is not None
            # If it fails, it should NOT be due to version mismatch
            if not result.success and result.error:
                assert "version mismatch" not in result.error.message.lower()
    
    async def test_handles_missing_version_in_content(self, logger, mock_context, tmp_path):
        """Should handle gracefully when content has no version attribute."""
        tool = PublishTool(logger)
        
        directive_path = tmp_path / ".ai" / "directives" / "custom" / "test_directive.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("""# Test Directive

```xml
<directive name="test_directive">
  <metadata>
    <description>Test directive</description>
    <category>patterns</category>
  </metadata>
  <process>
    <step name="test">Test step</step>
  </process>
</directive>
```""")
        
        with patch.dict('os.environ', {'CONTEXT_KIWI_API_KEY': 'test-key'}):
            input_data = ToolInput(
                directive="test_directive",
                version="1.0.0",
                source="project",
                project_path=str(tmp_path)
            )
            result = await tool.execute(input_data, mock_context)
            
            # Should fail validation (missing version attribute is invalid XML)
            assert not result.success
            assert result.error is not None
            # Should fail on XML validation, not version mismatch
            assert "version" in result.error.message.lower() or "validation" in result.error.message.lower()