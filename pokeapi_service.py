import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

logger = logging.getLogger(__name__)

POKEAPI_BASE = "https://pokeapi.co/api/v2"

_cache = {}


def _get_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def _get_cached(key):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < Config.CACHE_TTL_SECONDS:
            logger.info("Cache hit for %s", key)
            return data
    return None


def _set_cached(key, data):
    _cache[key] = (time.time(), data)


def get_pokemon(name_or_id):
    key = f"pokemon:{str(name_or_id).lower()}"
    cached = _get_cached(key)
    if cached is not None:
        return cached
    try:
        session = _get_session()
        url = f"{POKEAPI_BASE}/pokemon/{str(name_or_id).lower()}"
        logger.info("Fetching Pokémon from PokeAPI: %s", name_or_id)
        resp = session.get(url, timeout=10)
        if resp.status_code == 404:
            return {"error": f"Pokémon '{name_or_id}' not found"}
        resp.raise_for_status()
        data = resp.json()
        result = {
            "id": data["id"],
            "name": data["name"],
            "height": data["height"],
            "weight": data["weight"],
            "base_experience": data.get("base_experience"),
            "types": [t["type"]["name"] for t in data["types"]],
            "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
            "sprite": data["sprites"]["front_default"],
            "sprite_shiny": data["sprites"]["front_shiny"],
        }
        _set_cached(key, result)
        return result
    except requests.exceptions.RequestException as e:
        logger.error("PokeAPI error for %s: %s", name_or_id, e)
        if key in _cache:
            logger.info("Returning stale cache for %s", key)
            return _cache[key][1]
        return {"error": f"PokeAPI unavailable: {str(e)}"}


def check_health():
    try:
        session = _get_session()
        resp = session.get(f"{POKEAPI_BASE}/pokemon/1", timeout=5)
        resp.raise_for_status()
        return True, "reachable"
    except requests.exceptions.RequestException as e:
        return False, str(e)
