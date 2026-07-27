from pathlib import Path

import yaml

from geotask_core import __version__
from geotask_core._version import __version__ as source_version


ROOT = Path(__file__).resolve().parents[1]


def test_package_version_has_one_source_of_truth() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))

    assert 'dynamic = ["version"]' in pyproject
    assert 'version = {attr = "geotask_core._version.__version__"}' in pyproject
    assert __version__ == source_version == "0.1.1"
    assert citation["version"] == source_version
