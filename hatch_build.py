"""Build-time PyPI long description.

The committed README.md tags its calcbloc.com and itmarkerz.co.in links with ``utm_medium=readme`` (the copy
GitHub shows). The copy PyPI shows is generated here, at build time, with ``utm_medium=pypi`` so analytics can
tell the two apart. hatchling runs this metadata hook for every sdist, wheel and editable build; README.md
itself is never rewritten.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict

README = "README.md"
PYPI_MEDIUM = "pypi"
_README_UTM = re.compile(r"(utm_source=calcbloc-python&(?:amp;)?utm_medium=)readme\b")


def pypi_readme(text: str) -> str:
    """Return the README text with this repository's ``utm_medium=readme`` tags switched to ``pypi``."""
    new, count = _README_UTM.subn(r"\g<1>" + PYPI_MEDIUM, text)
    if count == 0:
        raise ValueError("README.md has no utm_source=calcbloc-python&utm_medium=readme links to retag")
    return new


try:
    from hatchling.metadata.plugin.interface import MetadataHookInterface
except ImportError:  # imported by the tests without hatchling installed
    MetadataHookInterface = None  # type: ignore[assignment,misc]

if MetadataHookInterface is not None:

    class PyPIReadmeHook(MetadataHookInterface):
        PLUGIN_NAME = "custom"

        def update(self, metadata: Dict[str, Any]) -> None:
            with open(os.path.join(self.root, README), encoding="utf-8") as fh:
                text = fh.read()
            metadata["readme"] = {"content-type": "text/markdown", "text": pypi_readme(text)}
