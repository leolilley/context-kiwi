"""Semantic versioning utilities."""

import re
from typing import Tuple


def parse(version: str) -> Tuple[int, int, int, str]:
    """Parse semver string into (major, minor, patch, prerelease)."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', version)
    if not match:
        raise ValueError(f"Invalid semver: {version}")
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        match.group(4) or "",
    )


def satisfies(version: str, constraint: str) -> bool:
    """
    Check if a version satisfies a constraint.
    
    Supports:
        - Exact: "1.0.0"
        - Caret: "^1.0.0" (compatible with 1.x.x)
        - Tilde: "~1.0.0" (compatible with 1.0.x)
        - Latest: "*" or "latest"
    """
    if constraint in ("*", "latest"):
        return True
    
    try:
        v_major, v_minor, v_patch, _ = parse(version)
    except ValueError:
        return False
    
    # Caret: ^1.2.3 means >=1.2.3 and <2.0.0
    if constraint.startswith("^"):
        try:
            c_major, c_minor, c_patch, _ = parse(constraint[1:])
            if v_major != c_major:
                return False
            if v_major == 0:
                return v_minor == c_minor and v_patch >= c_patch
            return (v_minor > c_minor) or (v_minor == c_minor and v_patch >= c_patch)
        except ValueError:
            return False
    
    # Tilde: ~1.2.3 means >=1.2.3 and <1.3.0
    if constraint.startswith("~"):
        try:
            c_major, c_minor, c_patch, _ = parse(constraint[1:])
            return v_major == c_major and v_minor == c_minor and v_patch >= c_patch
        except ValueError:
            return False
    
    # Exact match
    try:
        c_major, c_minor, c_patch, _ = parse(constraint)
        return v_major == c_major and v_minor == c_minor and v_patch == c_patch
    except ValueError:
        return False

