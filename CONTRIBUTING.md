# Contributing to GeoTask

Thank you for your interest in contributing.

## Setup

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
pip install -e .
pip install pytest
```

## Running Tests

```bash
pytest
```

## Code Style

- Python 3.10+
- Type annotations for public functions
- Docstrings for public API
- No external network calls in Core
- No GIS framework dependencies (no Shapely, GeoPandas, GDAL)
- Only required dependency: PyYAML

## Architecture Boundaries

GeoTask Core must not import from `geotask_runtime` or `geotask_domain_packs`.

## PR Process

1. Fork the repository
2. Create a feature branch
3. Write tests for new behavior
4. Ensure all existing tests pass (`pytest`)
5. Update documentation if needed
6. Open a pull request

Pull requests must pass CI checks for tests, build, boundary verification, public-content scanning, and SHA-256 integrity verification.

## CLI

Use the `geotask` command. The `stir` command is a historical compatibility entry
point and should not be used in new code.

## Questions

Open an issue on GitHub.
