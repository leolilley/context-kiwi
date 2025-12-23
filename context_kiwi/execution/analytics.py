"""
Run history and analytics utilities.

Provides:
- Logging runs to history
- Analyzing directive performance
- Identifying failing patterns

Logs are stored in the project's .ai/.runs/ directory.
"""

import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_history_file() -> Path:
    """Get path to history file in user space."""
    from context_kiwi.config import get_user_home
    return get_user_home() / ".runs" / "history.jsonl"


def _ensure_dir(history_file: Path):
    """Ensure runs directory exists."""
    history_file.parent.mkdir(parents=True, exist_ok=True)


def log_run(
    directive: str,
    status: str,
    duration_sec: float,
    inputs: Dict,
    project: Optional[str] = None,
    outputs: Optional[Dict] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    Log a run to ~/.context-kiwi/.runs/history.jsonl.
    
    Args:
        directive: Name of the directive
        status: "loaded", "success", "error", "validation_failed"
        duration_sec: How long the run took
        inputs: Input parameters (will be summarized)
        project: Project name/path this was run in
        outputs: Output data (will be summarized)
        error: Error message if failed
        metadata: Additional metadata
        
    Returns:
        The logged run entry
    """
    history_file = _get_history_file()
    _ensure_dir(history_file)
    
    # Summarize inputs/outputs to avoid huge logs
    def summarize(data, max_items=5):
        if not data:
            return None
        if isinstance(data, dict):
            return {k: v for i, (k, v) in enumerate(data.items()) if i < max_items}
        return data
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "directive": directive,
        "status": status,
        "duration_sec": round(duration_sec, 2),
        "project": project,
        "inputs": summarize(inputs),
        "outputs": summarize(outputs),
        "error": error,
        "metadata": metadata
    }
    
    # Remove None values
    entry = {k: v for k, v in entry.items() if v is not None}
    
    with open(history_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    logger.info(f"Logged run: {directive} -> {status} ({duration_sec:.1f}s)")
    return entry


def get_run_history(
    days: int = 30, 
    directive: Optional[str] = None,
    project: Optional[str] = None
) -> List[Dict]:
    """
    Load run history from the last N days.
    
    Args:
        days: Number of days of history to load
        directive: Optional filter by directive name
        project: Optional filter by project
        
    Returns:
        List of run entries, most recent first
    """
    history_file = _get_history_file()
    if not history_file.exists():
        return []
    
    cutoff = datetime.now() - timedelta(days=days)
    runs = []
    
    with open(history_file, 'r') as f:
        for line in f:
            if line.strip():
                run = json.loads(line)
                run_time = datetime.fromisoformat(run['timestamp'])
                
                if run_time > cutoff:
                    if directive and run['directive'] != directive:
                        continue
                    if project and run.get('project') != project:
                        continue
                    runs.append(run)
    
    return sorted(runs, key=lambda x: x['timestamp'], reverse=True)


def _make_stats_entry() -> Dict[str, Any]:
    """Create a fresh stats entry for defaultdict."""
    return {
        'success': 0, 
        'error': 0, 
        'partial': 0,
        'total_duration': 0.0,
        'errors': []
    }


def directive_stats(
    days: int = 30,
    project: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate success rate and performance stats per directive.
    
    Args:
        days: Number of days to analyze
        project: Optional filter by project
        
    Returns:
        Dictionary of directive stats
    """
    runs = get_run_history(days=days, project=project)
    stats: Dict[str, Dict[str, Any]] = defaultdict(_make_stats_entry)
    
    for run in runs:
        d = run['directive']
        stats[d]['total_duration'] += run.get('duration_sec', 0)
        
        if run['status'] == 'success':
            stats[d]['success'] += 1
        elif run['status'] == 'partial_success':
            stats[d]['partial'] += 1
        else:
            stats[d]['error'] += 1
            if run.get('error'):
                stats[d]['errors'].append(run['error'])
    
    result = {}
    for d, s in stats.items():
        total = s['success'] + s['error'] + s['partial']
        result[d] = {
            'total_runs': total,
            'success_rate': s['success'] / total if total > 0 else 0,
            'partial_rate': s['partial'] / total if total > 0 else 0,
            'error_rate': s['error'] / total if total > 0 else 0,
            'avg_duration_sec': s['total_duration'] / total if total > 0 else 0,
            'common_errors': list(set(s['errors']))[:3]
        }
    
    return result


def identify_anneal_candidates(
    min_runs: int = 3,
    success_threshold: float = 0.8,
    days: int = 30,
    project: Optional[str] = None
) -> List[Dict]:
    """
    Identify directives that need annealing (improvement) based on performance.
    
    Args:
        min_runs: Minimum runs to consider
        success_threshold: Directives below this rate are candidates
        days: Number of days to analyze
        project: Optional filter by project
        
    Returns:
        List of directives that need attention
    """
    stats = directive_stats(days=days, project=project)
    
    candidates = []
    for directive, s in stats.items():
        if s['total_runs'] >= min_runs and s['success_rate'] < success_threshold:
            candidates.append({
                'directive': directive,
                'success_rate': s['success_rate'],
                'total_runs': s['total_runs'],
                'common_errors': s['common_errors'],
                'recommendation': 'Use anneal_directive to improve'
            })
    
    return sorted(candidates, key=lambda x: x['success_rate'])


def recent_failures(
    count: int = 10,
    project: Optional[str] = None
) -> List[Dict]:
    """
    Get recent failures for debugging.
    
    Args:
        count: Number of recent failures to return
        project: Optional filter by project
        
    Returns:
        List of failed runs with details
    """
    runs = get_run_history(days=7, project=project)
    failures = [r for r in runs if r['status'] == 'error']
    return failures[:count]
