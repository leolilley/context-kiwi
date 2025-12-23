"""Tests for context loading."""

from context_kiwi.execution.context import (
    load_context,
    get_tech_stack_list,
    has_context,
    get_context_summary
)


class TestLoadContext:
    """Test context loading."""
    
    def test_load_context_with_ai_directory(self, tmp_path):
        """Should load context from .ai/ directory."""
        ai_path = tmp_path / ".ai"
        ai_path.mkdir()
        
        project_context_file = ai_path / "project_context.md"
        project_context_file.write_text("# Project Context\n\n- Python\n- React")
        
        patterns_dir = ai_path / "patterns"
        patterns_dir.mkdir()
        (patterns_dir / "api.md").write_text("# API Pattern")
        
        context = load_context(project_path=tmp_path)
        
        assert 'project_context' in context
        assert 'Python' in context['project_context']
        assert 'patterns' in context
        assert 'api' in context['patterns']
    
    def test_load_context_missing_ai_directory(self, tmp_path):
        """Should return setup message when .ai/ doesn't exist."""
        context = load_context(project_path=tmp_path)
        
        assert 'setup_required' in context
        assert context['setup_required'] is True
        assert 'suggestion' in context
    
    def test_load_context_partial(self, tmp_path):
        """Should load available context even if some files are missing."""
        ai_path = tmp_path / ".ai"
        ai_path.mkdir()
        
        project_context_file = ai_path / "project_context.md"
        project_context_file.write_text("# Project Context")
        
        context = load_context(project_path=tmp_path)
        
        assert 'project_context' in context
        assert context['project_context'] is not None
        if 'patterns' in context:
            assert context['patterns'] == {}


class TestGetTechStackList:
    """Test tech stack list extraction from project_context.md."""
    
    def test_extract_tech_stack_list(self, tmp_path):
        """Should extract tech stack as list from project_context.md."""
        ai_path = tmp_path / ".ai"
        ai_path.mkdir()
        
        project_context_file = ai_path / "project_context.md"
        project_context_file.write_text("# Project Context\n\nPrimary: React 18\nSecondary: TypeScript, Tailwind CSS")
        
        tech_list = get_tech_stack_list(project_path=tmp_path)
        
        assert isinstance(tech_list, list)
        assert len(tech_list) > 0
    
    def test_extract_tech_stack_missing_file(self, tmp_path):
        """Should return empty list when project_context.md doesn't exist."""
        tech_list = get_tech_stack_list(project_path=tmp_path)
        
        assert isinstance(tech_list, list)
        assert len(tech_list) == 0


class TestHasContext:
    """Test context existence check."""
    
    def test_has_context_true(self, tmp_path):
        """Should return True when .ai/ exists with project_context.md."""
        ai_path = tmp_path / ".ai"
        ai_path.mkdir()
        
        project_context_file = ai_path / "project_context.md"
        project_context_file.write_text("# Project Context\n\n- Python")
        
        assert has_context(project_path=tmp_path) is True
    
    def test_has_context_false(self, tmp_path):
        """Should return False when .ai/ doesn't exist."""
        assert has_context(project_path=tmp_path) is False


class TestGetContextSummary:
    """Test context summary generation."""
    
    def test_get_context_summary(self, tmp_path):
        """Should generate context summary."""
        ai_path = tmp_path / ".ai"
        ai_path.mkdir()
        
        project_context_file = ai_path / "project_context.md"
        project_context_file.write_text("# Project Context\n\n- Python")
        
        summary = get_context_summary(project_path=tmp_path)
        
        assert isinstance(summary, dict)
        assert summary['has_context'] is True
        assert summary['project_context'] is True
    
    def test_get_context_summary_missing(self, tmp_path):
        """Should return dict when context is missing."""
        summary = get_context_summary(project_path=tmp_path)
        
        assert isinstance(summary, dict)
        assert summary['has_context'] is False
