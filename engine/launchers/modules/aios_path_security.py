"""Path validation helpers for filesystem-backed API routes."""

import re
from pathlib import Path


_APP_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def resolve_app_save_path(data_dir, slug):
    """Return a contained JSON record path for a simple app slug."""
    if not isinstance(slug, str) or not _APP_SLUG.fullmatch(slug):
        raise ValueError("invalid application slug")

    root = Path(data_dir).resolve()
    target = (root / f"{slug}.json").resolve()
    if target.parent != root:
        raise ValueError("application record path escapes data directory")
    return target
