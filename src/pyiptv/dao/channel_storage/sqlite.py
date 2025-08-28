import re
import sqlite3
from functools import lru_cache
from typing import Dict, List, Optional, Set

from pyiptv.dao.channel_storage.base import BaseChannelStorage
from pyiptv.dto.channel import ChannelEntity
from pyiptv.enum.channel_type import ChannelType


def _clean_token(token: str) -> str:
    """Remove special characters from token for FTS safety."""
    return re.sub(r"[^\w\s]", "", token).strip()


def generate_ngrams(text: str, n: int = 3) -> str:
    """Generate space-separated n-grams (bigrams, trigrams) + full words from cleaned text."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)  # Remove punctuation
    grams: Set[str] = set()
    grams.add(text)
    words: List[str] = text.split()
    grams.update(words)

    for size in range(2, n + 1):
        for word in words:
            for i in range(len(word) - size + 1):
                grams.add(word[i : i + size])
    return " ".join(grams)


class ChannelStorageSQLite(BaseChannelStorage):
    def __init__(self, filepath: str) -> None:
        self.conn: sqlite3.Connection = sqlite3.connect(filepath)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _table_for_type(self, channel_type: ChannelType) -> str:
        return f"channels_{channel_type.value}"

    def _fts_table_for_type(self, channel_type: ChannelType) -> str:
        return f"channels_{channel_type.value}_fts"

    def _create_schema(self) -> None:
        cursor: sqlite3.Cursor = self.conn.cursor()

        for t in ChannelType:
            main: str = self._table_for_type(t)
            fts: str = self._fts_table_for_type(t)

            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {main} (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    playable_url TEXT NOT NULL
                ) WITHOUT ROWID
                """
            )

            cursor.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {fts}
                USING fts5(
                    id UNINDEXED,
                    name,
                    playable_url,
                    ngrams,
                    tokenize='porter'
                )
                """
            )

        self.conn.commit()

    def save_channel(self, channel: ChannelEntity) -> None:
        cursor: sqlite3.Cursor = self.conn.cursor()
        main_table: str = self._table_for_type(channel.type)
        fts_table: str = self._fts_table_for_type(channel.type)

        self.conn.execute("BEGIN")

        cursor.execute(
            f"""
            INSERT OR REPLACE INTO {main_table} (id, name, playable_url)
            VALUES (?, ?, ?)
            """,
            (channel.id, channel.name, channel.playable_url),
        )

        ngrams: str = generate_ngrams(channel.name)
        cursor.execute(
            f"""
            INSERT OR REPLACE INTO {fts_table} (id, name, playable_url, ngrams)
            VALUES (?, ?, ?, ?)
            """,
            (channel.id, channel.name, channel.playable_url, ngrams),
        )

        self.conn.commit()

    def save_channel_bulk(self, channels: List[ChannelEntity]) -> None:
        cursor: sqlite3.Cursor = self.conn.cursor()
        self.conn.execute("BEGIN")

        grouped: Dict[ChannelType, List[ChannelEntity]] = {}
        for ch in channels:
            grouped.setdefault(ch.type, []).append(ch)

        for t, batch in grouped.items():
            main_table: str = self._table_for_type(t)
            fts_table: str = self._fts_table_for_type(t)

            main_rows: List[tuple[str, str, str]] = [
                (ch.id, ch.name, ch.playable_url) for ch in batch
            ]
            fts_rows: List[tuple[str, str, str, str]] = [
                (ch.id, ch.name, ch.playable_url, generate_ngrams(ch.name))
                for ch in batch
            ]

            cursor.executemany(
                f"""
                INSERT OR REPLACE INTO {main_table} (id, name, playable_url)
                VALUES (?, ?, ?)
                """,
                main_rows,
            )

            cursor.executemany(
                f"""
                INSERT OR REPLACE INTO {fts_table} (id, name, playable_url, ngrams)
                VALUES (?, ?, ?, ?)
                """,
                fts_rows,
            )

        self.conn.commit()

    @lru_cache(maxsize=8192)
    def get_channel(self, channel_id: str) -> Optional[ChannelEntity]:
        cursor: sqlite3.Cursor = self.conn.cursor()
        for t in ChannelType:
            table: str = self._table_for_type(t)
            cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (channel_id,))
            row: Optional[sqlite3.Row] = cursor.fetchone()
            if row:
                return self._row_to_entity(row, t)
        return None

    @lru_cache(maxsize=8192)
    def search_by_name_and_type(
        self, name: str, channel_type: ChannelType
    ) -> List[ChannelEntity]:
        cursor: sqlite3.Cursor = self.conn.cursor()
        tokens: List[str] = [_clean_token(tok) for tok in name.lower().split()]
        match_query: str = " AND ".join(f'ngrams:"{tok}"' for tok in tokens if tok)
        fts_table: str = self._fts_table_for_type(channel_type)

        cursor.execute(
            f"""
            SELECT id, name, playable_url, bm25({fts_table}) AS score
            FROM {fts_table}
            WHERE {fts_table} MATCH ?
            ORDER BY score
            """,
            (match_query,),
        )

        rows: List[sqlite3.Row] = cursor.fetchall()
        return [self._row_to_entity(r, channel_type) for r in rows]

    def _row_to_entity(
        self, row: sqlite3.Row, channel_type: ChannelType
    ) -> ChannelEntity:
        return ChannelEntity(
            id=row["id"],
            name=row["name"],
            playable_url=row["playable_url"],
            type=channel_type,
        )
