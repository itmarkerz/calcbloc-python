"""The PyPI long description (built by hatch_build.py) tags links utm_medium=pypi; README.md keeps readme."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _hook_module():
    spec = importlib.util.spec_from_file_location("calcbloc_hatch_build", ROOT / "hatch_build.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pypi_readme_retags_every_readme_link() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "utm_medium=readme" in readme
    assert "utm_medium=pypi" not in readme
    pypi = _hook_module().pypi_readme(readme)
    assert "utm_medium=readme" not in pypi
    assert pypi.count("utm_source=calcbloc-python&utm_medium=pypi&utm_campaign=itmarkerz-oss") == readme.count(
        "utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss"
    )
    # Only the medium changes.
    assert pypi.replace("utm_medium=pypi", "utm_medium=readme") == readme


def test_pypi_readme_refuses_untagged_text() -> None:
    with pytest.raises(ValueError):
        _hook_module().pypi_readme("# no tagged links here")
