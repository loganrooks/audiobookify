"""Packaging invariants.

The distribution name (``audiobookifier``) deliberately differs from the console
script name (``audiobookify``) and from the import package (``epub2tts_edge``).
Three different names for the same project is a standing trap: any code that
looks up its own version has to name the *distribution*, and the obvious guess
is wrong.

It is worse than a plain typo here, because ``audiobookify`` is a real, still-
published project on PyPI owned by someone else's account. A stale lookup does
not raise -- it silently resolves to that other package's version, or falls back
to ``0.0.0.dev0``. Either way ``--version`` lies.

This was a live regression: renaming the distribution left both lookups pointing
at ``audiobookify``, and ``audiobookify --version`` reported ``0.0.0.dev0``. The
release workflow asserts the reported version matches the tag, so it would have
failed the release rather than shipping a wrong number -- but only at release
time, which is the expensive place to find out.
"""

import re
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _declared_distribution_name() -> str:
    return tomllib.loads(PYPROJECT.read_text())["project"]["name"]


@pytest.fixture(scope="module")
def installed_version() -> str:
    """The version recorded under the name pyproject.toml declares."""
    name = _declared_distribution_name()
    try:
        return pkg_version(name)
    except PackageNotFoundError:  # pragma: no cover - source tree without install
        pytest.skip(f"{name} is not installed; run `pip install -e .`")


def test_package_version_uses_the_declared_distribution_name(installed_version):
    """``epub2tts_edge.__version__`` must resolve, not fall back."""
    import epub2tts_edge

    assert epub2tts_edge.__version__ == installed_version
    assert epub2tts_edge.__version__ != "0.0.0.dev0"


def test_cli_version_uses_the_declared_distribution_name(installed_version):
    """``--version`` must report the same thing the package does."""
    from epub2tts_edge.epub2tts_edge import _get_version

    assert _get_version() == installed_version
    assert _get_version() != "0.0.0.dev0"


def _normalize(name: str) -> str:
    """PEP 503 name normalization, enough for the comparison we need."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_base(requirement: str) -> str:
    """The project name at the head of a requirement string."""
    return _normalize(re.split(r"[\[<>=!~; ]", requirement.strip(), maxsplit=1)[0])


def test_nothing_depends_on_the_foreign_audiobookify_project():
    """``audiobookify`` on PyPI is a different project, owned by another account.

    The ``all`` extra self-references this project, so it named ``audiobookify``
    before the rename. Left unchanged, ``pip install audiobookifier[all]`` would
    resolve that name against PyPI and pull the unrelated package -- an install
    that succeeds while being silently wrong.
    """
    data = tomllib.loads(PYPROJECT.read_text())
    project = data["project"]
    declared = _normalize(project["name"])

    groups = {"dependencies": project.get("dependencies", [])}
    groups.update(project.get("optional-dependencies", {}))

    for group, requirements in groups.items():
        for requirement in requirements:
            base = _requirement_base(requirement)
            assert base != "audiobookify", (
                f"{group!r} requires {requirement!r}, which resolves to the "
                f"unrelated PyPI project 'audiobookify'; this distribution is "
                f"{declared!r}"
            )
