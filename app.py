import logging

from flask import Flask, jsonify, render_template, request

import db
import pokeapi_service
from config import Config
from logging_config import setup_logging

app = Flask(__name__)
app.config.from_object(Config)
setup_logging(app)

logger = logging.getLogger(__name__)

with app.app_context():
    try:
        db.init_db()
        logger.info("Database initialised successfully")
    except Exception as e:
        logger.warning("Could not initialise database: %s", e)


@app.route("/health")
def health():
    db_ok, db_msg = db.check_health()
    poke_ok, poke_msg = pokeapi_service.check_health()
    healthy = db_ok and poke_ok
    status_code = 200 if healthy else 503
    return jsonify({
        "status": "healthy" if healthy else "degraded",
        "dependencies": {
            "database": {"ok": db_ok, "detail": db_msg},
            "pokeapi": {"ok": poke_ok, "detail": poke_msg},
        },
    }), status_code


@app.route("/status")
def status():
    db_ok, db_msg = db.check_health()
    poke_ok, poke_msg = pokeapi_service.check_health()
    return render_template(
        "status.html",
        db_ok=db_ok,
        db_msg=db_msg,
        poke_ok=poke_ok,
        poke_msg=poke_msg,
    )


@app.route("/api/pokemon", methods=["GET"])
def list_favourites():
    try:
        favourites = db.get_all_favourites()
        return jsonify(favourites)
    except Exception as e:
        logger.error("Failed to list favourites: %s", e)
        return jsonify({"error": "Database unavailable"}), 503


@app.route("/api/pokemon", methods=["POST"])
def add_favourite():
    data = request.get_json(force=True)
    pokemon_name = data.get("pokemon_name")
    if not pokemon_name:
        return jsonify({"error": "pokemon_name is required"}), 400
    check = pokeapi_service.get_pokemon(pokemon_name)
    if "error" in check:
        return jsonify({"error": f"Could not find Pokémon: {pokemon_name}"}), 404
    try:
        favourite = db.add_favourite(
            pokemon_name,
            data.get("nickname", ""),
            data.get("notes", ""),
        )
        return jsonify(favourite), 201
    except Exception as e:
        logger.error("Failed to save Pokémon: %s", e)
        return jsonify({"error": "Database unavailable"}), 503


@app.route("/api/pokemon/<int:fav_id>", methods=["GET"])
def get_favourite(fav_id):
    try:
        favourite = db.get_favourite(fav_id)
        if favourite is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(favourite)
    except Exception as e:
        logger.error("Failed to get favourite: %s", e)
        return jsonify({"error": "Database unavailable"}), 503


@app.route("/api/pokemon/<int:fav_id>", methods=["DELETE"])
def delete_favourite(fav_id):
    try:
        deleted = db.delete_favourite(fav_id)
        if not deleted:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        logger.error("Failed to delete favourite: %s", e)
        return jsonify({"error": "Database unavailable"}), 503


@app.route("/api/pokemon/<int:fav_id>/details")
def pokemon_details(fav_id):
    try:
        favourite = db.get_favourite(fav_id)
    except Exception as e:
        logger.error("DB error fetching favourite %s: %s", fav_id, e)
        return jsonify({"error": "Database unavailable"}), 503
    if favourite is None:
        return jsonify({"error": "Not found"}), 404
    poke_data = pokeapi_service.get_pokemon(favourite["pokemon_name"])
    return jsonify({
        "saved": favourite,
        "pokemon": poke_data,
    })


@app.route("/")
def dashboard():
    try:
        favourites = db.get_all_favourites()
    except Exception:
        favourites = []
    enriched = []
    for f in favourites:
        poke = pokeapi_service.get_pokemon(f["pokemon_name"])
        enriched.append({"saved": f, "pokemon": poke})
    return render_template("dashboard.html", favourites=enriched)


if __name__ == "__main__":
    app.run(debug=True)
