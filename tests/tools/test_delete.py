"""Tests for delete_directive handler."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from context_kiwi.tools.directives.delete import (
    delete_directive_handler,
    _delete_from_project,
    _delete_from_user,
    _delete_from_registry,
    _cleanup_empty_dirs
)
from context_kiwi.mcp_types import ToolContext


@pytest.fixture
def mock_context():
    """Mock ToolContext."""
    return ToolContext(
        userId="test_user",
        requestId="test_req",
        permissions=["execute", "read", "write"],
        accessLevel="read-write",
        timestamp=1234567890.0,
        toolName="delete_directive"
    )


@pytest.fixture
def mock_db():
    """Mock DirectiveDB."""
    db = Mock()
    db.get.return_value = Mock(name="test_directive", category="patterns")
    db.delete.return_value = True
    return db


class TestDeleteFromProject:
    """Test deletion from project space."""
    
    def test_delete_from_project_success(self, tmp_path):
        """Should delete directive file from project space."""
        directive_path = tmp_path / ".ai" / "directives" / "patterns" / "test_directive.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("# Test Directive\n<directive name='test_directive'></directive>")
        
        project_path = tmp_path / ".ai" / "directives"
        success, message, file_path = _delete_from_project("test_directive", project_path)
        
        assert success is True
        assert "Deleted from project space" in message
        assert file_path is not None
        assert not directive_path.exists()
    
    def test_delete_from_project_not_found(self, tmp_path):
        """Should return success if directive not found (idempotent)."""
        project_path = tmp_path / ".ai" / "directives"
        success, message, file_path = _delete_from_project("nonexistent", project_path)
        
        assert success is True
        assert "not found" in message.lower()
        assert file_path is None
    
    def test_delete_from_project_with_subcategory(self, tmp_path):
        """Should delete directive from nested subcategory folder."""
        directive_path = tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints" / "test_api.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("# Test API\n<directive name='test_api'></directive>")
        
        project_path = tmp_path / ".ai" / "directives"
        success, message, file_path = _delete_from_project("test_api", project_path)
        
        assert success is True
        assert not directive_path.exists()
    
    def test_delete_from_project_cleanup_empty_dirs(self, tmp_path):
        """Should cleanup empty directories when enabled."""
        directive_path = tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints" / "test_api.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("# Test API\n<directive name='test_api'></directive>")
        
        project_path = tmp_path / ".ai" / "directives"
        success, message, file_path = _delete_from_project("test_api", project_path, cleanup_empty_dirs=True)
        
        assert success is True
        assert not directive_path.exists()
        # Empty subcategory directory should be removed
        assert not (tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints").exists()
        # Category directory should remain (even if empty, we preserve it)
        assert (tmp_path / ".ai" / "directives" / "patterns").exists()


class TestDeleteFromUser:
    """Test deletion from user space."""
    
    def test_delete_from_user_success(self, tmp_path):
        """Should delete directive file from user space and lockfile."""
        user_path = tmp_path / "user" / "directives"
        directive_path = user_path / "core" / "test_directive.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("# Test Directive\n<directive name='test_directive'></directive>")
        
        with patch('context_kiwi.tools.directives.delete.remove_locked_directive') as mock_remove:
            success, message, file_path = _delete_from_user("test_directive", user_path)
            
            assert success is True
            assert "Deleted from user space" in message
            assert file_path is not None
            assert not directive_path.exists()
            mock_remove.assert_called_once_with("test_directive")
    
    def test_delete_from_user_not_found(self, tmp_path):
        """Should return success if directive not found (idempotent)."""
        user_path = tmp_path / "user" / "directives"
        
        with patch('context_kiwi.tools.directives.delete.remove_locked_directive') as mock_remove:
            success, message, file_path = _delete_from_user("nonexistent", user_path)
            
            assert success is True
            assert "not found" in message.lower()
            # Should still try to remove from lockfile
            mock_remove.assert_called_once_with("nonexistent")


class TestDeleteFromRegistry:
    """Test deletion from registry."""
    
    def test_delete_from_registry_success(self, mock_db):
        """Should delete directive from registry."""
        success, message = _delete_from_registry("test_directive", mock_db)
        
        assert success is True
        assert "Deleted from registry" in message
        mock_db.get.assert_called_once_with("test_directive")
        mock_db.delete.assert_called_once_with("test_directive")
    
    def test_delete_from_registry_not_found(self):
        """Should return success if directive not found (idempotent)."""
        db = Mock()
        db.get.return_value = None
        
        success, message = _delete_from_registry("nonexistent", db)
        
        assert success is True
        assert "not found" in message.lower()


class TestDeleteDirectiveHandler:
    """Test main delete_directive_handler."""
    
    @pytest.mark.asyncio
    async def test_delete_from_registry_only(self, mock_context, mock_db):
        """Should delete from registry only (default behavior)."""
        with patch('context_kiwi.tools.directives.delete.DirectiveDB', return_value=mock_db):
            result = await delete_directive_handler(
                {"name": "test_directive", "from": "registry"},
                mock_context
            )
            
            assert result["status"] == "deleted"
            assert result["deleted_from"]["registry"]["success"] is True
            assert result["deleted_from"]["user"]["success"] is False  # Not attempted
            assert result["deleted_from"]["project"]["success"] is False  # Not attempted
    
    @pytest.mark.asyncio
    async def test_delete_from_user_only(self, mock_context, tmp_path):
        """Should delete from user space only."""
        user_path = tmp_path / "user" / "directives" / "core"
        user_path.mkdir(parents=True, exist_ok=True)
        directive_path = user_path / "test_directive.md"
        directive_path.write_text("# Test\n<directive name='test_directive'></directive>")
        
        with patch('context_kiwi.tools.directives.delete.get_user_home', return_value=tmp_path / "user"), \
             patch('context_kiwi.tools.directives.delete.remove_locked_directive'):
            
            result = await delete_directive_handler(
                {"name": "test_directive", "from": "user"},
                mock_context
            )
            
            assert result["status"] == "deleted"
            assert result["deleted_from"]["user"]["success"] is True
            assert not directive_path.exists()
    
    @pytest.mark.asyncio
    async def test_delete_from_project_only(self, mock_context, tmp_path):
        """Should delete from project space only."""
        project_path = tmp_path / ".ai" / "directives" / "patterns"
        project_path.mkdir(parents=True, exist_ok=True)
        directive_path = project_path / "test_directive.md"
        directive_path.write_text("# Test\n<directive name='test_directive'></directive>")
        
        result = await delete_directive_handler(
            {
                "name": "test_directive",
                "from": "project",
                "project_path": str(tmp_path)
            },
            mock_context
        )
        
        assert result["status"] == "deleted"
        assert result["deleted_from"]["project"]["success"] is True
        assert not directive_path.exists()
    
    @pytest.mark.asyncio
    async def test_delete_from_all_tiers(self, mock_context, mock_db, tmp_path):
        """Should delete from all three tiers."""
        # Setup project file
        project_path = tmp_path / ".ai" / "directives" / "patterns"
        project_path.mkdir(parents=True, exist_ok=True)
        project_file = project_path / "test_directive.md"
        project_file.write_text("# Test\n<directive name='test_directive'></directive>")
        
        # Setup user file
        user_path = tmp_path / "user" / "directives" / "core"
        user_path.mkdir(parents=True, exist_ok=True)
        user_file = user_path / "test_directive.md"
        user_file.write_text("# Test\n<directive name='test_directive'></directive>")
        
        with patch('context_kiwi.tools.directives.delete.DirectiveDB', return_value=mock_db), \
             patch('context_kiwi.tools.directives.delete.get_user_home', return_value=tmp_path / "user"), \
             patch('context_kiwi.tools.directives.delete.remove_locked_directive'):
            
            result = await delete_directive_handler(
                {
                    "name": "test_directive",
                    "from": "all",
                    "project_path": str(tmp_path)
                },
                mock_context
            )
            
            assert result["status"] == "deleted"
            assert result["deleted_from"]["registry"]["success"] is True
            assert result["deleted_from"]["user"]["success"] is True
            assert result["deleted_from"]["project"]["success"] is True
            assert not project_file.exists()
            assert not user_file.exists()
    
    @pytest.mark.asyncio
    async def test_delete_with_cleanup_empty_dirs(self, mock_context, tmp_path):
        """Should cleanup empty directories when enabled."""
        directive_path = tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints" / "test_api.md"
        directive_path.parent.mkdir(parents=True, exist_ok=True)
        directive_path.write_text("# Test\n<directive name='test_api'></directive>")
        
        result = await delete_directive_handler(
            {
                "name": "test_api",
                "from": "project",
                "cleanup_empty_dirs": True,
                "project_path": str(tmp_path)
            },
            mock_context
        )
        
        assert result["status"] == "deleted"
        assert not directive_path.exists()
        # Empty subcategory directory should be removed
        assert not (tmp_path / ".ai" / "directives" / "patterns" / "api-endpoints").exists()
    
    @pytest.mark.asyncio
    async def test_delete_missing_name_parameter(self, mock_context):
        """Should return error when name is missing."""
        result = await delete_directive_handler({}, mock_context)
        
        assert result["status"] == "error"
        assert "Missing required parameter: name" in result["message"]
    
    @pytest.mark.asyncio
    async def test_delete_invalid_from_parameter(self, mock_context):
        """Should return error for invalid 'from' parameter."""
        result = await delete_directive_handler(
            {"name": "test", "from": "invalid"},
            mock_context
        )
        
        assert result["status"] == "error"
        assert "Invalid 'from' parameter" in result["message"]
    
    @pytest.mark.asyncio
    async def test_delete_not_found_in_any_tier(self, mock_context):
        """Should return error if directive not found in any tier when from='all'."""
        db = Mock()
        db.get.return_value = None
        
        with patch('context_kiwi.tools.directives.delete.DirectiveDB', return_value=db):
            result = await delete_directive_handler(
                {"name": "nonexistent", "from": "all"},
                mock_context
            )
            
            assert result["status"] == "error"
            assert "not found in any tier" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_delete_partial_success(self, mock_context, tmp_path):
        """Should return partial status when some tiers succeed and others fail."""
        # Setup project file (will succeed)
        project_path = tmp_path / ".ai" / "directives" / "patterns"
        project_path.mkdir(parents=True, exist_ok=True)
        project_file = project_path / "test_directive.md"
        project_file.write_text("# Test\n<directive name='test_directive'></directive>")
        
        # Setup user file (will succeed)
        user_path = tmp_path / "user" / "directives" / "core"
        user_path.mkdir(parents=True, exist_ok=True)
        user_file = user_path / "test_directive.md"
        user_file.write_text("# Test\n<directive name='test_directive'></directive>")
        
        # Registry will fail (actual failure, not just not found)
        db = Mock()
        db.get.return_value = Mock(name="test_directive")  # Exists
        db.delete.return_value = False  # Delete fails
        
        with patch('context_kiwi.tools.directives.delete.DirectiveDB', return_value=db), \
             patch('context_kiwi.tools.directives.delete.get_user_home', return_value=tmp_path / "user"), \
             patch('context_kiwi.tools.directives.delete.remove_locked_directive'):
            
            result = await delete_directive_handler(
                {
                    "name": "test_directive",
                    "from": "all",
                    "project_path": str(tmp_path)
                },
                mock_context
            )
            
            assert result["status"] == "partial"
            assert result["deleted_from"]["project"]["success"] is True
            assert result["deleted_from"]["user"]["success"] is True
            assert result["deleted_from"]["registry"]["success"] is False  # Actually failed
            assert "Partially deleted" in result["message"] or "some tiers failed" in result["message"].lower()


class TestCleanupEmptyDirs:
    """Test empty directory cleanup."""
    
    def test_cleanup_empty_dirs(self, tmp_path):
        """Should remove empty parent directories."""
        file_path = tmp_path / "patterns" / "api-endpoints" / "test.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("test")
        
        base_path = tmp_path
        file_path.unlink()
        
        _cleanup_empty_dirs(file_path, base_path)
        
        # Empty directories should be removed
        assert not (tmp_path / "patterns" / "api-endpoints").exists()
        # Base path should remain
        assert tmp_path.exists()
    
    def test_cleanup_stops_at_base_path(self, tmp_path):
        """Should stop cleanup at base_path."""
        file_path = tmp_path / "patterns" / "api-endpoints" / "test.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("test")
        
        base_path = tmp_path / "patterns"
        file_path.unlink()
        
        _cleanup_empty_dirs(file_path, base_path)
        
        # Should only remove api-endpoints, not patterns
        assert not (tmp_path / "patterns" / "api-endpoints").exists()
        assert (tmp_path / "patterns").exists()
    
    def test_cleanup_preserves_non_empty_dirs(self, tmp_path):
        """Should preserve directories that still have files."""
        file_path = tmp_path / "patterns" / "api-endpoints" / "test.md"
        other_file = tmp_path / "patterns" / "api-endpoints" / "other.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("test")
        other_file.write_text("other")
        
        base_path = tmp_path
        file_path.unlink()
        
        _cleanup_empty_dirs(file_path, base_path)
        
        # Directory should remain (has other.md)
        assert (tmp_path / "patterns" / "api-endpoints").exists()
        assert other_file.exists()

