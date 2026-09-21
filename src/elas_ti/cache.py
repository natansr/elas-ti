"""Cache privado: índices HMAC e respostas sem nomes em texto claro."""

import hashlib
import hmac
import json
import os
import sqlite3
from pathlib import Path

FIELDS = (
    "gender",
    "probability",
    "count",
    "country_id",
    "name_mode",
    "timestamp_consulta",
)


class GenderCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        key_path = path.with_suffix(".key")
        if not key_path.exists() and path.exists():
            with sqlite3.connect(path) as existing:
                if existing.execute("PRAGMA user_version").fetchone()[0] >= 2:
                    raise ValueError(
                        "Chave do cache ausente; restaure a chave original"
                    )
        if not key_path.exists():
            with key_path.open("xb") as stream:
                stream.write(os.urandom(32))
            key_path.chmod(0o600)
        self.key = key_path.read_bytes()
        if len(self.key) != 32:
            raise ValueError("Chave de cache inválida")
        self.connection = sqlite3.connect(path)
        path.chmod(0o600)
        self.connection.execute("PRAGMA secure_delete=ON")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS predictions (
            name TEXT NOT NULL, country TEXT NOT NULL, mode TEXT NOT NULL,
            response TEXT NOT NULL, PRIMARY KEY (name, country, mode))""")
        if self.connection.execute("PRAGMA user_version").fetchone()[0] < 2:
            rows = self.connection.execute("SELECT * FROM predictions").fetchall()
            with self.connection:
                self.connection.execute("DELETE FROM predictions")
                for name, country, mode, response in rows:
                    self._put(name, country, mode, json.loads(response))
                self.connection.execute("PRAGMA user_version=2")
            self.connection.execute("VACUUM")
        self.connection.commit()

    def _token(self, name):
        return hmac.new(self.key, name.encode("utf-8"), hashlib.sha256).hexdigest()

    def get(self, name: str, country: str, mode: str) -> dict | None:
        row = self.connection.execute(
            "SELECT response FROM predictions WHERE name=? AND country=? AND mode=?",
            (self._token(name), country, mode),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def _put(self, name, country, mode, response):
        clean = {k: response[k] for k in FIELDS if k in response}
        self.connection.execute(
            "INSERT OR REPLACE INTO predictions VALUES (?, ?, ?, ?)",
            (self._token(name), country, mode, json.dumps(clean)),
        )

    def put(self, name: str, country: str, mode: str, response: dict):
        with self.connection:
            self._put(name, country, mode, response)

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
