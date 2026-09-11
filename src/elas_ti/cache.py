"""Cache local de respostas; não é um cadastro de identidades."""
import json
import sqlite3
from pathlib import Path


class GenderCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute('''CREATE TABLE IF NOT EXISTS predictions (
            name TEXT NOT NULL, country TEXT NOT NULL, mode TEXT NOT NULL,
            response TEXT NOT NULL, PRIMARY KEY (name, country, mode))''')
        self.connection.commit()

    def get(self, name: str, country: str, mode: str) -> dict | None:
        row = self.connection.execute(
            "SELECT response FROM predictions WHERE name=? AND country=? AND mode=?",
            (name, country, mode),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, name: str, country: str, mode: str, response: dict):
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO predictions VALUES (?, ?, ?, ?)",
                (name, country, mode, json.dumps(response, ensure_ascii=False)),
            )

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
