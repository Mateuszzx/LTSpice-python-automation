"""Locate schematics that ship with this repository."""

from __future__ import annotations

from pathlib import Path


def _looks_like_project_root(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (path / "models").is_dir()


def project_root() -> Path:
    """Return the checkout that contains ``pyproject.toml`` and ``models/``.

    Walks upward from the current working directory first, so notebooks work
    whether Jupyter starts in ``notebooks/`` or at the repository root. Falls
    back to the installed package location, which covers an editable install.
    """
    starts = [Path.cwd().resolve(), Path(__file__).resolve()]
    seen: set[Path] = set()
    for start in starts:
        for candidate in (start, *start.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if _looks_like_project_root(candidate):
                return candidate
    raise FileNotFoundError(
        "Could not find the ltspice-python-automation checkout "
        "(expected pyproject.toml next to a models/ directory). "
        "Open the notebooks from that repository."
    )


def models_dir(*parts: str) -> Path:
    """Return ``models/`` or a path inside it, and require that path to exist."""
    path = project_root().joinpath("models", *parts)
    if not path.exists():
        raise FileNotFoundError(f"Model path not found: {path}")
    return path
