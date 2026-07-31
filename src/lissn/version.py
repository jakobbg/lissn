"""
Version and Git metadata helper for lissn.
Provides dynamic application versioning, Git commit hash, commit message,
and GitHub repository links.
"""

from functools import lru_cache
from pathlib import Path
import re
import subprocess
from typing import Any, Dict

from lissn import __version__

DEFAULT_GITHUB_URL = "https://github.com/jakobbg/lissn"


def _clean_git_url(raw_url: str) -> str:
    """Convert git remote URL (SSH or HTTPS with .git) to standard HTTP GitHub URL."""
    if not raw_url:
        return DEFAULT_GITHUB_URL
    url = raw_url.strip()
    # Convert git@github.com:user/repo.git -> https://github.com/user/repo
    if url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "https://github.com/")
    # Strip trailing .git
    if url.endswith(".git"):
        url = url[:-4]
    return url if url.startswith("http") else DEFAULT_GITHUB_URL


@lru_cache(maxsize=1)
def get_app_metadata() -> Dict[str, Any]:
    """
    Retrieve and cache application metadata including version, git commit hash,
    commit title, and GitHub project link.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent

    git_commit = "unknown"
    git_commit_full = "unknown"
    git_commit_name = ""
    github_url = DEFAULT_GITHUB_URL

    try:
        # Get short commit hash
        res_short = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res_short.returncode == 0 and res_short.stdout.strip():
            git_commit = res_short.stdout.strip()

        # Get full commit hash
        res_full = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res_full.returncode == 0 and res_full.stdout.strip():
            git_commit_full = res_full.stdout.strip()

        # Get commit subject/title
        res_msg = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res_msg.returncode == 0 and res_msg.stdout.strip():
            git_commit_name = res_msg.stdout.strip()

        # Get git remote origin URL
        res_url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res_url.returncode == 0 and res_url.stdout.strip():
            github_url = _clean_git_url(res_url.stdout.strip())
    except Exception:
        # Fallback cleanly if git command is not available or directory is not a git repo
        pass

    if git_commit != "unknown":
        git_commit_url = f"{github_url}/commit/{git_commit}"
    else:
        git_commit_url = github_url

    release_url = f"{github_url}/releases/tag/v{__version__}"

    if git_commit_name:
        served_by_info = f"Served by lissn v{__version__} (commit {git_commit}: {git_commit_name})"
    else:
        served_by_info = f"Served by lissn v{__version__} (commit {git_commit})"

    tooltip_info = f"lissn v{__version__} (commit {git_commit})"

    return {
        "app_name": "lissn",
        "app_version": __version__,
        "git_commit": git_commit,
        "git_commit_full": git_commit_full,
        "git_commit_name": git_commit_name,
        "github_url": github_url,
        "git_commit_url": git_commit_url,
        "release_url": release_url,
        "served_by_info": served_by_info,
        "tooltip_info": tooltip_info,
    }

