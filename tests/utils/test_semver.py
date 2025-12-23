"""Tests for semver utilities."""

import pytest
from context_kiwi.utils import semver


class TestSemver:
    """Test semver utilities."""
    
    def test_parse_version(self):
        """Should parse version string."""
        major, minor, patch, prerelease = semver.parse("1.2.3")
        assert major == 1
        assert minor == 2
        assert patch == 3
        assert prerelease == ""
    
    def test_parse_version_with_prerelease(self):
        """Should parse version with prerelease."""
        major, minor, patch, prerelease = semver.parse("1.2.3-alpha.1")
        assert major == 1
        assert minor == 2
        assert patch == 3
        assert prerelease == "alpha.1"
    
    def test_parse_invalid_version(self):
        """Should raise ValueError for invalid version."""
        with pytest.raises(ValueError):
            semver.parse("invalid")
    
    def test_satisfies_exact(self):
        """Should check exact version match."""
        assert semver.satisfies("1.0.0", "1.0.0") is True
        assert semver.satisfies("1.0.1", "1.0.0") is False
    
    def test_satisfies_caret(self):
        """Should check caret constraint."""
        assert semver.satisfies("1.2.3", "^1.0.0") is True
        assert semver.satisfies("2.0.0", "^1.0.0") is False
        assert semver.satisfies("1.0.0", "^1.0.0") is True
    
    def test_satisfies_tilde(self):
        """Should check tilde constraint."""
        assert semver.satisfies("1.2.3", "~1.2.0") is True
        assert semver.satisfies("1.3.0", "~1.2.0") is False
        assert semver.satisfies("1.2.0", "~1.2.0") is True
    
    def test_satisfies_latest(self):
        """Should always satisfy latest constraint."""
        assert semver.satisfies("1.0.0", "*") is True
        assert semver.satisfies("1.0.0", "latest") is True
        assert semver.satisfies("any.version", "latest") is True
