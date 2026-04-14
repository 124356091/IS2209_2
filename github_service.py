"""External API integration: GitHub API with retry/backoff and caching."""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

logger = logging.getLogger(__name__)

# Simple in-memory cache: key -> (timestamp, data)
_cache = {}


def _get_session():
    """Create a requests session with retry/backoff."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    if Config.GITHUB_TOKEN:
        session.headers["Authorization"] = f"token {Config.GITHUB_TOKEN}"
    session.headers["Accept"] = "application/vnd.github.v3+json"
    return session


def _get_cached(key):
    """Return cached data if still valid, else None."""
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < Config.CACHE_TTL_SECONDS:
            logger.info("Cache hit for %s", key)
            return data
    return None


def _set_cached(key, data):
    """Store data in cache."""
    _cache[key] = (time.time(), data)


def get_repo_info(owner_repo):
    """Fetch repository info from GitHub. Returns dict or error dict."""
    cached = _get_cached(f"repo:{owner_repo}")
    if cached is not None:
        return cached

    try:
        session = _get_session()
        url = f"{Config.GITHUB_API_BASE}/repos/{owner_repo}"
        logger.info("Fetching GitHub repo: %s", owner_repo)
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "language": data.get("language"),
            "updated_at": data.get("updated_at"),
            "html_url": data.get("html_url"),
        }
        _set_cached(f"repo:{owner_repo}", result)
        return result
    except requests.exceptions.RequestException as e:
        logger.error("GitHub API error for %s: %s", owner_repo, e)
        # Return cached data even if expired, as a fallback
        if f"repo:{owner_repo}" in _cache:
            logger.info("Returning stale cache for %s", owner_repo)
            return _cache[f"repo:{owner_repo}"][1]
        return {"error": f"GitHub API unavailable: {str(e)}"}


def check_health():
    """Check if GitHub API is reachable. Returns (ok, message)."""
    try:
        session = _get_session()
        resp = session.get(f"{Config.GITHUB_API_BASE}/rate_limit", timeout=5)
        resp.raise_for_status()
        remaining = resp.json().get("rate", {}).get("remaining", "unknown")
        return True, f"reachable (rate limit remaining: {remaining})"
    except requests.exceptions.RequestException as e:
        return False, str(e)
