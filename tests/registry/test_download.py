"""Tests for registry download."""

import pytest
from unittest.mock import Mock, patch
from context_kiwi.registry.download import serve_directive, get_directive_info


@pytest.mark.asyncio
class TestRegistryDownload:
    """Test registry download functions."""
    
    async def test_serve_directive(self, logger, mock_supabase):
        """Should serve directive content from database."""
        from context_kiwi.db.directives import DirectiveDB
        
        mock_db = Mock(spec=DirectiveDB)
        mock_db.get_content = Mock(return_value="# Test Directive\n\n<steps>Test steps</steps>")
        mock_db.increment_downloads = Mock()
        mock_db._require_db = Mock()
        
        with patch('context_kiwi.registry.download.DirectiveDB', return_value=mock_db):
            content = await serve_directive("test_directive")
            
            assert content is not None
            assert "Test Directive" in content
            mock_db.get_content.assert_called_once()
            mock_db.increment_downloads.assert_called_once()
    
    async def test_serve_directive_not_found(self, logger):
        """Should raise FileNotFoundError when directive not found."""
        from context_kiwi.db.directives import DirectiveDB
        
        mock_db = Mock(spec=DirectiveDB)
        mock_db.get_content = Mock(return_value=None)
        mock_db._require_db = Mock()
        
        with patch('context_kiwi.registry.download.DirectiveDB', return_value=mock_db):
            with pytest.raises(FileNotFoundError):
                await serve_directive("nonexistent")
    
    async def test_get_directive_info(self, logger):
        """Should get directive metadata."""
        from context_kiwi.db.directives import DirectiveDB
        
        mock_directive = Mock()
        mock_directive.name = "test_directive"
        mock_directive.category = "core"
        mock_directive.description = "Test"
        mock_directive.is_official = True
        mock_directive.download_count = 10
        mock_directive.quality_score = 0.9
        mock_directive.tech_stack = ["Python"]
        mock_directive.current_version = Mock(version="1.0.0")
        
        mock_db = Mock(spec=DirectiveDB)
        mock_db.get = Mock(return_value=mock_directive)
        mock_db.get_versions = Mock(return_value=["1.0.0", "1.1.0"])
        mock_db._require_db = Mock()
        
        with patch('context_kiwi.registry.download.DirectiveDB', return_value=mock_db):
            info = await get_directive_info("test_directive")
            
            assert info is not None
            assert info['name'] == "test_directive"
            assert info['latest_version'] == "1.0.0"
            assert len(info['available_versions']) == 2
    
    async def test_get_directive_info_not_found(self, logger):
        """Should return None when directive not found."""
        from context_kiwi.db.directives import DirectiveDB
        
        mock_db = Mock(spec=DirectiveDB)
        mock_db.get = Mock(return_value=None)
        mock_db._require_db = Mock()
        
        with patch('context_kiwi.registry.download.DirectiveDB', return_value=mock_db):
            info = await get_directive_info("nonexistent")
            
            assert info is None
