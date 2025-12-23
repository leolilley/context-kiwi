"""
Context Loader

Loads project context from the .ai/ directory:
- project_context.md - Auto-generated comprehensive context
- design_system.md - Styling conventions
- patterns/*.md - Code patterns
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def load_project_context(project_path: Path | None = None) -> str | None:
    """
    Load project_context.md if it exists.
    
    Args:
        project_path: Project root (default: cwd)
        
    Returns:
        Contents of project_context.md or None if not found
    """
    ai_path = (project_path or Path.cwd()) / ".ai"
    project_context_file = ai_path / "project_context.md"
    
    if project_context_file.exists():
        logger.debug("Loaded project_context.md")
        return project_context_file.read_text()
    
    return None


def load_context(project_path: Path | None = None) -> Dict[str, Any]:
    """
    Load project context from .ai/ directory.
    
    Args:
        project_path: Project root (default: cwd)
        
    Returns:
        {
            "project_context": str,  # Contents of project_context.md
            "design_system": str,    # Contents of design_system.md (optional)
            "patterns": {            # Contents of patterns/*.md
                "api": str,
                "components": str,
                ...
            }
        }
        
    Example:
        context = load_context()
        if "setup_required" in context:
            print("Run 'init' first to create .ai/")
        elif context.get("project_context"):
            print(f"Project context loaded")
    """
    ai_path = (project_path or Path.cwd()) / ".ai"
    
    if not ai_path.exists():
        logger.warning(f".ai/ directory not found at {ai_path}")
        return {
            "note": ".ai/ directory not found. This is expected for new projects.",
            "setup_required": True,
            "suggestion": "Run the 'init' directive to create the .ai/ structure: run('init')"
        }
    
    context = {}
    
    # Project context (primary context - auto-generated)
    project_context_file = ai_path / "project_context.md"
    if project_context_file.exists():
        context["project_context"] = project_context_file.read_text()
        logger.debug("Loaded project_context.md")
    else:
        context["project_context"] = None
        logger.warning("project_context.md not found. Run 'run(\"context\")' to generate it.")
    
    # Design system (optional)
    design_system_file = ai_path / "design_system.md"
    if design_system_file.exists():
        context["design_system"] = design_system_file.read_text()
        logger.debug("Loaded design_system.md")
    
    # Patterns (all .md files in patterns/)
    patterns_dir = ai_path / "patterns"
    if patterns_dir.exists():
        context["patterns"] = {}
        for pattern_file in patterns_dir.glob("*.md"):
            pattern_name = pattern_file.stem
            context["patterns"][pattern_name] = pattern_file.read_text()
            logger.debug(f"Loaded pattern: {pattern_name}")
    
    return context


def get_tech_stack_list(project_path: Path | None = None) -> list[str]:
    """
    Extract tech stack as a list from project_context.md.
    
    Parses the markdown to find technology names.
    
    Returns:
        List of technology names (e.g., ["React", "TypeScript", "Tailwind"])
    """
    ai_path = (project_path or Path.cwd()) / ".ai"
    project_context_file = ai_path / "project_context.md"
    
    if not project_context_file.exists():
        return []
    
    content = project_context_file.read_text()
    
    # Simple extraction: look for common patterns
    # - "Primary: React 18"
    # - "- React"
    # - "Framework: Next.js"
    # - "### Languages", "### Frameworks" sections
    
    techs = []
    lines = content.split("\n")
    
    for line in lines:
        line = line.strip()
        
        # Skip headers and empty lines
        if line.startswith("#") or not line:
            continue
        
        # Extract from "- Technology" format
        if line.startswith("- "):
            tech = line[2:].strip()
            # Remove version numbers like "React 18" -> "React"
            tech = tech.split()[0] if tech else ""
            if tech and not tech.startswith("*"):
                techs.append(tech)
        
        # Extract from "Key: Value" format
        elif ":" in line:
            value = line.split(":", 1)[1].strip()
            if value and not value.startswith("["):
                # Remove version numbers
                tech = value.split()[0] if value else ""
                if tech:
                    techs.append(tech)
    
    return techs


def has_context(project_path: Path | None = None) -> bool:
    """Check if project has .ai/ context set up."""
    ai_path = (project_path or Path.cwd()) / ".ai"
    return ai_path.exists() and (ai_path / "project_context.md").exists()


def get_context_summary(project_path: Path | None = None) -> Dict[str, Any]:
    """
    Get a summary of available context.
    
    Returns:
        {
            "has_context": bool,
            "project_context": bool,
            "design_system": bool,
            "pattern_count": int,
            "patterns": ["api", "components", ...]
        }
    """
    ai_path = (project_path or Path.cwd()) / ".ai"
    
    if not ai_path.exists():
        return {"has_context": False}
    
    summary = {
        "has_context": True,
        "project_context": (ai_path / "project_context.md").exists(),
        "design_system": (ai_path / "design_system.md").exists(),
        "pattern_count": 0,
        "patterns": []
    }
    
    patterns_dir = ai_path / "patterns"
    if patterns_dir.exists():
        patterns = list(patterns_dir.glob("*.md"))
        summary["pattern_count"] = len(patterns)
        summary["patterns"] = [p.stem for p in patterns]
    
    return summary

