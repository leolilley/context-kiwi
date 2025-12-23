"""Tests for preflight validation."""

from unittest.mock import Mock, patch
import os
from context_kiwi.execution.preflight import (
    check_credentials,
    check_packages,
    validate_inputs,
    validate_inputs_simple,
    run_preflight
)


class TestCheckCredentials:
    """Test credential checking."""
    
    def test_all_credentials_present(self):
        """Should pass when all credentials are present."""
        with patch.dict(os.environ, {'API_KEY': 'test', 'SECRET': 'test'}):
            result = check_credentials(['API_KEY', 'SECRET'])
            assert result['status'] == 'pass'
            assert 'missing' not in result
    
    def test_missing_credentials(self):
        """Should fail when credentials are missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = check_credentials(['API_KEY', 'SECRET'])
            assert result['status'] == 'fail'
            assert 'missing' in result
            assert len(result['missing']) == 2
    
    def test_partial_credentials(self):
        """Should fail when some credentials are missing."""
        with patch.dict(os.environ, {'API_KEY': 'test'}):
            result = check_credentials(['API_KEY', 'SECRET'])
            assert result['status'] == 'fail'
            assert 'SECRET' in result['missing']


class TestCheckPackages:
    """Test package checking."""
    
    def test_package_check_npm(self, tmp_path):
        """Should check npm packages."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = check_packages([{'name': 'react', 'manager': 'npm'}], project_path=tmp_path)
            assert result['status'] == 'pass'
    
    def test_package_check_pip(self):
        """Should check pip packages."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = check_packages([{'name': 'requests', 'manager': 'pip'}])
            assert result['status'] == 'pass'
    
    def test_missing_package(self):
        """Should fail when package is missing."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            result = check_packages([{'name': 'missing-pkg', 'manager': 'npm'}])
            assert result['status'] == 'fail'
            assert 'missing' in result


class TestValidateInputs:
    """Test input validation."""
    
    def test_valid_inputs(self):
        """Should pass with valid inputs."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }
        inputs = {"name": "test"}
        
        result = validate_inputs(inputs, schema)
        assert result['valid'] is True
    
    def test_invalid_inputs(self):
        """Should fail with invalid inputs."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        inputs = {}
        
        result = validate_inputs(inputs, schema)
        assert result['valid'] is False
        assert 'errors' in result
    
    def test_simple_validation(self):
        """Should validate inputs with simple rules."""
        rules = [
            {"field": "name", "type": "string", "required": True},
            {"field": "count", "type": "integer"}
        ]
        inputs = {"name": "test", "count": 5}
        
        result = validate_inputs_simple(inputs, rules)
        assert result['valid'] is True
    
    def test_simple_validation_failure(self):
        """Should fail simple validation with wrong types."""
        rules = [
            {"field": "name", "type": "string", "required": True},
            {"field": "count", "type": "integer"}
        ]
        inputs = {"name": 123, "count": "not a number"}
        
        result = validate_inputs_simple(inputs, rules)
        assert result['valid'] is False
        assert len(result['errors']) > 0


class TestRunPreflight:
    """Test full preflight validation."""
    
    def test_preflight_success(self):
        """Should pass all preflight checks."""
        inputs = {"name": "test"}
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }
        
        with patch('context_kiwi.execution.preflight.check_credentials', return_value={'status': 'pass'}), \
             patch('context_kiwi.execution.preflight.validate_inputs', return_value={'valid': True}):
            
            result = run_preflight(
                inputs=inputs,
                input_schema=input_schema
            )
            assert result['pass'] is True
            assert len(result['blockers']) == 0
    
    def test_preflight_missing_credentials(self):
        """Should fail when credentials are missing."""
        inputs = {}
        required_credentials = ["API_KEY"]
        
        with patch('context_kiwi.execution.preflight.check_credentials', return_value={'status': 'fail', 'missing': ['API_KEY']}):
            result = run_preflight(
                inputs=inputs,
                required_credentials=required_credentials
            )
            assert result['pass'] is False
            assert len(result['blockers']) > 0
            assert any('API_KEY' in blocker for blocker in result['blockers'])
    
    def test_preflight_invalid_inputs(self):
        """Should fail when inputs are invalid."""
        inputs = {}
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        
        with patch('context_kiwi.execution.preflight.check_credentials', return_value={'status': 'pass'}), \
             patch('context_kiwi.execution.preflight.validate_inputs', return_value={'valid': False, 'errors': ['name is required']}):
            
            result = run_preflight(
                inputs=inputs,
                input_schema=input_schema
            )
            assert result['pass'] is False
            assert len(result['blockers']) > 0
