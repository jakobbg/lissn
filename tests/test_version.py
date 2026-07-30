"""
Unit tests for lissn.version module.
"""

from unittest.mock import patch

from lissn.version import _clean_git_url, get_app_metadata


def test_clean_git_url():
    assert _clean_git_url("https://github.com/jakobbg/lissn.git") == "https://github.com/jakobbg/lissn"
    assert _clean_git_url("git@github.com:jakobbg/lissn.git") == "https://github.com/jakobbg/lissn"
    assert _clean_git_url("") == "https://github.com/jakobbg/lissn"


def test_get_app_metadata_keys():
    meta = get_app_metadata()
    assert meta["app_name"] == "lissn"
    assert meta["app_version"] == "0.4.0"
    assert "git_commit" in meta
    assert "git_commit_full" in meta
    assert "git_commit_name" in meta
    assert "github_url" in meta
    assert "git_commit_url" in meta
    assert "Served by lissn" in meta["served_by_info"]
    assert "lissn v" in meta["tooltip_info"]


def test_get_app_metadata_fallback():
    get_app_metadata.cache_clear()
    with patch("subprocess.run", side_effect=Exception("Git not found")):
        meta = get_app_metadata()
        assert meta["git_commit"] == "unknown"
        assert meta["git_commit_full"] == "unknown"
        assert meta["git_commit_name"] == ""
        assert meta["github_url"] == "https://github.com/jakobbg/lissn"
        assert meta["git_commit_url"] == "https://github.com/jakobbg/lissn"
        assert "Served by lissn v0.4.0 (commit unknown)" in meta["served_by_info"]
        assert "lissn v0.4.0 (commit unknown)" in meta["tooltip_info"]
    get_app_metadata.cache_clear()
