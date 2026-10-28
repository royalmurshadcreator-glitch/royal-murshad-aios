"""Allowlisted static files and contained dashboard file resolution."""

import re
from pathlib import Path, PurePosixPath

from fastapi.staticfiles import StaticFiles


PUBLIC_UI_ALLOWED_FILES = frozenset(
    {"index.html", "app.js", "chat_client.js", "styles.css", "assets/royal-lion.png"}
)
DASHBOARD_PUBLIC_ALLOWED_FILES = frozenset(
    {
        "about.html", "aios-design-system.css", "contact.html", "demo.html",
        "faq.html", "features.html", "index.html", "pricing.html",
        "privacy.html", "status.html", "terms.html",
    }
)
DASHBOARD_ASSET_ALLOWED_FILES = frozenset(
    {
        "apple-touch-icon.png", "favicon-16x16.png", "favicon-32x32.png",
        "favicon.ico", "icon-192x192.png", "icon-512x512.png",
        "icon-maskable-192.png", "icon-maskable-512.png", "icon-master-1024.png",
    }
)
APP_DEPLOY_ALLOWED_SUFFIXES = frozenset({".html", ".js", ".css", ".jpg", ".jpeg", ".png", ".svg", ".webp", ".ico"})
_APP_DEPLOY_EXCLUDED_PARTS = frozenset(
    {".git", "node_modules", "__pycache__", "quarantine", "deprecated", "archive"}
)
_APP_DEPLOY_PREFIX = "Royal Murshad AIOS - royal-"
_APP_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def build_app_deploy_allowlist(apps_root):
    """Collect browser asset paths while excluding backups and runtime artifacts."""
    root = Path(apps_root).resolve(strict=True)
    allowed = set()
    for candidate in root.rglob("*"):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        relative = candidate.relative_to(root)
        parts = tuple(part.casefold() for part in relative.parts)
        if any(
            part in _APP_DEPLOY_EXCLUDED_PARTS or "backup" in part or "quarantine" in part
            for part in parts[:-1]
        ):
            continue
        if candidate.name.startswith(".") or candidate.suffix.casefold() not in APP_DEPLOY_ALLOWED_SUFFIXES:
            continue
        allowed.add(relative.as_posix())
    return frozenset(allowed)


def resolve_app_deployment_html(apps_root, slug):
    """Find one app's index page, validating the slug and final resolved path."""
    if not isinstance(slug, str) or not _APP_SLUG.fullmatch(slug):
        raise ValueError("invalid application slug")
    root = Path(apps_root).resolve(strict=True)
    target = (root / f"{_APP_DEPLOY_PREFIX}{slug}" / "index.html").resolve(strict=True)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("application page escapes deployment directory") from exc
    if not target.is_file() or target.suffix.casefold() != ".html":
        raise FileNotFoundError("application page not found")
    return target


class ApprovedStaticFiles(StaticFiles):
    """Serve only an explicit set of relative files from one directory."""

    def __init__(self, *, directory, allowed_paths, html=False):
        super().__init__(directory=directory, check_dir=True, html=html)
        self.allowed_paths = frozenset(allowed_paths)

    def lookup_path(self, path):
        normalized = PurePosixPath(str(path).replace("\\", "/")).as_posix()
        if normalized not in self.allowed_paths:
            return "", None
        return super().lookup_path(path)


def resolve_dashboard_html(dashboard_root, requested_path=""):
    """Resolve a dashboard HTML file without following paths outside its root."""
    raw_path = "" if requested_path is None else str(requested_path)
    relative = Path(raw_path)
    if relative.is_absolute() or relative.drive or relative.root or ".." in relative.parts:
        raise ValueError("dashboard path must stay inside the approved dashboard directory")

    root = Path(dashboard_root).resolve(strict=True)
    candidate = (root / relative).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("dashboard path must stay inside the approved dashboard directory") from exc

    if candidate.is_dir():
        for name in ("index.html", "dashboard.html", "app.html"):
            page = (candidate / name).resolve(strict=False)
            try:
                page.relative_to(root)
            except ValueError as exc:
                raise ValueError("dashboard page escapes the approved dashboard directory") from exc
            if page.is_file():
                return page
        raise FileNotFoundError("dashboard page not found")

    if candidate.is_file() and candidate.suffix.lower() == ".html":
        return candidate
    raise FileNotFoundError("dashboard page not found")
