"""Tests for directive finder utilities."""

from context_kiwi.utils.directive_finder import find_directive_file


class TestDirectiveFinder:
    """Test directive finder utilities."""
    
    def test_find_directive_in_project(self, tmp_path):
        """Should find directive in project space."""
        ai_path = tmp_path / ".ai" / "directives" / "custom"
        ai_path.mkdir(parents=True)
        
        directive_file = ai_path / "test_directive.md"
        directive_file.write_text("# Test\n\n<directive name=\"test_directive\">\n</directive>")
        
        base_path = tmp_path / ".ai" / "directives"
        path = find_directive_file("test_directive", base_path)
        
        assert path is not None
        assert path.exists()
    
    def test_find_directive_in_user_space(self, tmp_path):
        """Should find directive in user space."""
        user_path = tmp_path / "user" / "directives" / "core"
        user_path.mkdir(parents=True)
        
        directive_file = user_path / "test_directive.md"
        directive_file.write_text("# Test\n\n<directive name=\"test_directive\">\n</directive>")
        
        base_path = tmp_path / "user" / "directives"
        path = find_directive_file("test_directive", base_path)
        
        assert path is not None
        assert path.exists()
    
    def test_find_directive_not_found(self, tmp_path):
        """Should return None when directive not found."""
        base_path = tmp_path / ".ai" / "directives"
        path = find_directive_file("nonexistent", base_path)
        
        assert path is None
