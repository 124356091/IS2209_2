import psycopg

from config import Config


def get_connection():
    return psycopg.connect(Config.DATABASE_URL)


def check_health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True, "connected"
    except Exception as e:
        return False, str(e)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS favourites (
                    id SERIAL PRIMARY KEY,
                    pokemon_name VARCHAR(100) NOT NULL,
                    nickname VARCHAR(100) DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()


def get_all_favourites():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, pokemon_name, nickname, notes, created_at FROM favourites ORDER BY id"
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "pokemon_name": r[1],
                    "nickname": r[2],
                    "notes": r[3],
                    "created_at": r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ]


def get_favourite(fav_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, pokemon_name, nickname, notes, created_at FROM favourites WHERE id = %s",
                (fav_id,),
            )
            r = cur.fetchone()
            if r is None:
                return None
            return {
                "id": r[0],
                "pokemon_name": r[1],
                "nickname": r[2],
                "notes": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }


def add_favourite(pokemon_name, nickname="", notes=""):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO favourites (pokemon_name, nickname, notes) VALUES (%s, %s, %s) RETURNING id, created_at",
                (pokemon_name.lower(), nickname, notes),
            )
            row = cur.fetchone()
            conn.commit()
            return {
                "id": row[0],
                "pokemon_name": pokemon_name.lower(),
                "nickname": nickname,
                "notes": notes,
                "created_at": row[1].isoformat() if row[1] else None,
            }


def delete_favourite(fav_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM favourites WHERE id = %s", (fav_id,))
            conn.commit()
            return cur.rowcount > 0
