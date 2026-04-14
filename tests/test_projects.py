from unittest.mock import patch

SAMPLE_FAVOURITE = {
    "id": 1,
    "pokemon_name": "pikachu",
    "nickname": "Sparky",
    "notes": "My starter",
    "created_at": "2025-01-01T00:00:00",
}

SAMPLE_POKEMON = {
    "id": 25,
    "name": "pikachu",
    "height": 4,
    "weight": 60,
    "base_experience": 112,
    "types": ["electric"],
    "stats": {"hp": 35, "attack": 55, "defense": 40, "speed": 90},
    "sprite": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png",
    "sprite_shiny": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/25.png",
}


def test_list_favourites(client):
    with patch("app.db.get_all_favourites", return_value=[SAMPLE_FAVOURITE]):
        resp = client.get("/api/pokemon")
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data) == 1
        assert data[0]["pokemon_name"] == "pikachu"


def test_add_favourite(client):
    with patch("app.pokeapi_service.get_pokemon", return_value=SAMPLE_POKEMON), \
         patch("app.db.add_favourite", return_value=SAMPLE_FAVOURITE):
        resp = client.post("/api/pokemon", json={"pokemon_name": "pikachu", "nickname": "Sparky"})
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["pokemon_name"] == "pikachu"


def test_add_favourite_missing_name(client):
    resp = client.post("/api/pokemon", json={"nickname": "Sparky"})
    assert resp.status_code == 400
    assert "required" in resp.get_json()["error"]


def test_add_favourite_invalid_pokemon(client):
    with patch("app.pokeapi_service.get_pokemon", return_value={"error": "Pokémon 'notreal' not found"}):
        resp = client.post("/api/pokemon", json={"pokemon_name": "notreal"})
        assert resp.status_code == 404


def test_get_favourite(client):
    with patch("app.db.get_favourite", return_value=SAMPLE_FAVOURITE):
        resp = client.get("/api/pokemon/1")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == 1


def test_get_favourite_not_found(client):
    with patch("app.db.get_favourite", return_value=None):
        resp = client.get("/api/pokemon/999")
        assert resp.status_code == 404


def test_delete_favourite(client):
    with patch("app.db.delete_favourite", return_value=True):
        resp = client.delete("/api/pokemon/1")
        assert resp.status_code == 200


def test_returns_joined_result_when_both_sources_available(client):
    with patch("app.db.get_favourite", return_value=SAMPLE_FAVOURITE), \
         patch("app.pokeapi_service.get_pokemon", return_value=SAMPLE_POKEMON):
        resp = client.get("/api/pokemon/1/details")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["saved"]["pokemon_name"] == "pikachu"
        assert data["pokemon"]["stats"]["hp"] == 35
        assert data["pokemon"]["types"] == ["electric"]


def test_graceful_degradation_on_upstream_failure(client):
    with patch("app.db.get_favourite", return_value=SAMPLE_FAVOURITE), \
         patch("app.pokeapi_service.get_pokemon", return_value={"error": "PokeAPI unavailable: timeout"}):
        resp = client.get("/api/pokemon/1/details")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["saved"]["pokemon_name"] == "pikachu"
        assert "error" in data["pokemon"]


def test_db_unavailable_returns_503(client):
    with patch("app.db.get_all_favourites", side_effect=Exception("connection refused")):
        resp = client.get("/api/pokemon")
        assert resp.status_code == 503
