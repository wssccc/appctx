#!/usr/bin/env python3
"""
Script to bump version in pyproject.toml
Usage: python scripts/bump_version.py [major|minor|patch|version_number]
"""

import re
import sys
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    
    return match.group(1)


def bump_version(current_version, bump_type):
    """Bump version based on type"""
    major, minor, patch = map(int, current_version.split('.'))
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        # Assume it's a specific version number
        return bump_type


def update_version(new_version):
    """Update version in pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    
    # Update version
    new_content = re.sub(
        r'version = "[^"]+"',
        f'version = "{new_version}"',
        content
    )
    
    pyproject_path.write_text(new_content)
    print(f"Updated version to {new_version}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py [major|minor|patch|version_number]")
        sys.exit(1)
    
    bump_type = sys.argv[1]
    current_version = get_current_version()
    
    print(f"Current version: {current_version}")
    
    new_version = bump_version(current_version, bump_type)
    print(f"New version: {new_version}")
    
    update_version(new_version)


if __name__ == "__main__":
    main()