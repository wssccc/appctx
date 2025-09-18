# Release Guide

This document describes how to release a new version of appctx to PyPI.

## Prerequisites

1. Make sure you have the necessary permissions to create releases in the GitHub repository
2. Ensure all tests are passing on the main branch
3. Update the changelog/release notes if applicable

## Release Process

### 1. Update Version

Use the version bump script to update the version in `pyproject.toml`:

```bash
# For patch release (0.1.0 -> 0.1.1)
python scripts/bump_version.py patch

# For minor release (0.1.0 -> 0.2.0)
python scripts/bump_version.py minor

# For major release (0.1.0 -> 1.0.0)
python scripts/bump_version.py major

# For specific version
python scripts/bump_version.py 1.2.3
```

### 2. Commit and Push Changes

```bash
git add pyproject.toml
git commit -m "Bump version to X.Y.Z"
git push origin main
```

### 3. Create a GitHub Release

1. Go to the [Releases page](https://github.com/wssccc/appctx/releases)
2. Click "Create a new release"
3. Create a new tag with the version number (e.g., `v1.0.0`)
4. Set the release title to the version number
5. Add release notes describing the changes
6. Click "Publish release"

### 4. Automatic Publishing

Once the release is published, the GitHub Actions workflow will automatically:
- Build the package
- Run quality checks
- Publish to PyPI

## Testing the Release Process

You can test the release process by publishing to Test PyPI:

1. Go to the [Actions page](https://github.com/wssccc/appctx/actions)
2. Select the "Publish to PyPI" workflow
3. Click "Run workflow"
4. Check "Publish to Test PyPI instead of PyPI"
5. Click "Run workflow"

## Manual Publishing (if needed)

If you need to publish manually:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Check the package
twine check dist/*

# Upload to Test PyPI (optional)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## PyPI Configuration

The workflow uses PyPI's trusted publishing feature, which requires:

1. Configuring the PyPI project to trust the GitHub repository
2. Setting up the appropriate environment protection rules in GitHub

### Setting up Trusted Publishing

1. Go to your [PyPI account settings](https://pypi.org/manage/account/publishing/)
2. Add a new trusted publisher with:
   - PyPI Project Name: `appctx`
   - Owner: `wssccc`
   - Repository name: `appctx`
   - Workflow name: `publish.yml`
   - Environment name: `release`

### GitHub Environment Setup

1. Go to repository Settings > Environments
2. Create an environment named `release`
3. Add protection rules as needed (e.g., require reviews)

## Troubleshooting

- If the workflow fails, check the Actions logs for detailed error messages
- Ensure the version number follows semantic versioning
- Make sure all tests pass before creating a release
- Verify that the package builds correctly locally before releasing