"""Tests for analytics and run logging."""

import json
from unittest.mock import patch
from datetime import datetime, timedelta
from context_kiwi.execution.analytics import (
    log_run,
    get_run_history,
    directive_stats,
    identify_anneal_candidates,
    recent_failures
)


class TestLogRun:
    """Test run logging."""
    
    def test_log_run_success(self, tmp_path):
        """Should log successful run."""
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=tmp_path / "history.jsonl"), \
             patch('context_kiwi.execution.analytics._ensure_dir'):
            
            entry = log_run(
                directive="test_directive",
                status="success",
                duration_sec=1.5,
                inputs={"name": "test"},
                project="test_project"
            )
            
            assert entry['directive'] == "test_directive"
            assert entry['status'] == "success"
            assert entry['duration_sec'] == 1.5
            assert entry['project'] == "test_project"
    
    def test_log_run_error(self, tmp_path):
        """Should log failed run with error."""
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=tmp_path / "history.jsonl"), \
             patch('context_kiwi.execution.analytics._ensure_dir'):
            
            entry = log_run(
                directive="test_directive",
                status="error",
                duration_sec=0.5,
                inputs={},
                error="Test error message"
            )
            
            assert entry['status'] == "error"
            assert entry['error'] == "Test error message"
    
    def test_log_run_summarizes_inputs(self, tmp_path):
        """Should summarize large inputs."""
        large_inputs = {f"key_{i}": f"value_{i}" for i in range(10)}
        
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=tmp_path / "history.jsonl"), \
             patch('context_kiwi.execution.analytics._ensure_dir'):
            
            entry = log_run(
                directive="test",
                status="success",
                duration_sec=1.0,
                inputs=large_inputs
            )
            
            assert len(entry['inputs']) <= 5


class TestGetRunHistory:
    """Test run history retrieval."""
    
    def test_get_run_history(self, tmp_path):
        """Should retrieve run history."""
        history_file = tmp_path / "history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write test entries - make sure they're within the 30 day window
        now = datetime.now()
        entries = [
            {"timestamp": now.isoformat(), "directive": "test1", "status": "success", "duration_sec": 1.0},
            {"timestamp": (now - timedelta(days=1)).isoformat(), "directive": "test2", "status": "error", "duration_sec": 0.5}
        ]
        
        with open(history_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=history_file):
            history = get_run_history(days=30)
            
            assert len(history) >= 1
            assert history[0]['directive'] in ["test1", "test2"]
    
    def test_get_run_history_filter_by_directive(self, tmp_path):
        """Should filter history by directive."""
        history_file = tmp_path / "history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        entries = [
            {"timestamp": datetime.now().isoformat(), "directive": "test1", "status": "success", "duration_sec": 1.0},
            {"timestamp": datetime.now().isoformat(), "directive": "test2", "status": "success", "duration_sec": 1.0}
        ]
        
        with open(history_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=history_file):
            history = get_run_history(days=30, directive="test1")
            
            assert len(history) == 1
            assert history[0]['directive'] == "test1"


class TestDirectiveStats:
    """Test directive statistics."""
    
    def test_directive_stats(self, tmp_path):
        """Should calculate directive statistics."""
        history_file = tmp_path / "history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        entries = [
            {"timestamp": datetime.now().isoformat(), "directive": "test", "status": "success", "duration_sec": 1.0},
            {"timestamp": datetime.now().isoformat(), "directive": "test", "status": "error", "duration_sec": 0.5},
            {"timestamp": datetime.now().isoformat(), "directive": "test", "status": "success", "duration_sec": 1.0}
        ]
        
        with open(history_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=history_file):
            stats = directive_stats(days=30)
            
            assert "test" in stats
            assert stats["test"]["total_runs"] == 3
            assert stats["test"]["success_rate"] > 0
            assert stats["test"]["error_rate"] > 0


class TestIdentifyAnnealCandidates:
    """Test anneal candidate identification."""
    
    def test_identify_anneal_candidates(self, tmp_path):
        """Should identify directives that need improvement."""
        history_file = tmp_path / "history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        entries = [
            {"timestamp": datetime.now().isoformat(), "directive": "test1", "status": "error", "duration_sec": 0.5, "error": "Test error"},
            {"timestamp": datetime.now().isoformat(), "directive": "test1", "status": "error", "duration_sec": 0.5, "error": "Test error"},
            {"timestamp": datetime.now().isoformat(), "directive": "test1", "status": "error", "duration_sec": 0.5, "error": "Test error"},
            {"timestamp": datetime.now().isoformat(), "directive": "test2", "status": "success", "duration_sec": 1.0}
        ]
        
        with open(history_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=history_file):
            candidates = identify_anneal_candidates(days=30, min_runs=3, success_threshold=0.8)
            
            assert len(candidates) > 0
            assert any(c['directive'] == 'test1' for c in candidates)


class TestRecentFailures:
    """Test recent failure retrieval."""
    
    def test_recent_failures(self, tmp_path):
        """Should retrieve recent failures."""
        history_file = tmp_path / "history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        entries = [
            {"timestamp": datetime.now().isoformat(), "directive": "test", "status": "error", "error": "Test error", "duration_sec": 0.5},
            {"timestamp": datetime.now().isoformat(), "directive": "test", "status": "success", "duration_sec": 1.0}
        ]
        
        with open(history_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        with patch('context_kiwi.execution.analytics._get_history_file', return_value=history_file):
            failures = recent_failures(count=10)
            
            assert len(failures) == 1
            assert failures[0]['status'] == "error"
