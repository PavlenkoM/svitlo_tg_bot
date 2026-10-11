import csv
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from utils import styler


@dataclass
class ChatInfo:
    """Data class for chat information"""
    chat_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    date_added: str = ""
    is_active: bool = True
    show_partial: bool = False
    show_phases: bool = True


# Per-chat settings stored as columns: name -> default
CHAT_SETTINGS = {'show_partial': False, 'show_phases': True}


class StorageService:
    def __init__(self, db_file_path: str = None):
        """
        Initialize the chat storage service (SQLite)

        Args:
            db_file_path: Path to the SQLite database file. If None, uses default path.
        """
        current_dir = os.path.dirname(__file__)
        self.db_file_path = db_file_path or os.path.join(current_dir, 'chat_ids.db')

        self._create_tables()
        if db_file_path is None:
            self._migrate_from_csv(os.path.join(current_dir, 'chat_ids.csv'))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_file_path)

    def _create_tables(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id    INTEGER PRIMARY KEY,
                    username   TEXT    NOT NULL DEFAULT '',
                    first_name TEXT    NOT NULL DEFAULT '',
                    last_name  TEXT    NOT NULL DEFAULT '',
                    date_added TEXT    NOT NULL DEFAULT '',
                    is_active  INTEGER NOT NULL DEFAULT 1,
                    show_partial INTEGER NOT NULL DEFAULT 0,
                    show_phases  INTEGER NOT NULL DEFAULT 1
                )
            """)

            # Databases created before a chat setting existed
            columns = [row[1] for row in conn.execute("PRAGMA table_info(chats)")]
            for column, default in CHAT_SETTINGS.items():
                if column not in columns:
                    conn.execute(f"ALTER TABLE chats ADD COLUMN {column} INTEGER NOT NULL DEFAULT {int(default)}")

    def _migrate_from_csv(self, csv_file_path: str) -> None:
        """Import chats from the old CSV storage once, then keep the CSV as a backup"""
        if not os.path.exists(csv_file_path):
            return

        try:
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as file:
                rows = [(
                    int(row['chat_id']),
                    row.get('username') or '',
                    row.get('first_name') or '',
                    row.get('last_name') or '',
                    row.get('date_added') or '',
                    row.get('is_active', 'True').lower() == 'true',
                ) for row in csv.DictReader(file)]

            with closing(self._connect()) as conn, conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO chats (chat_id, username, first_name, last_name, date_added, is_active) "
                    "VALUES (?, ?, ?, ?, ?, ?)", rows
                )

            os.replace(csv_file_path, csv_file_path + '.migrated')
            styler.success(f"Migrated {len(rows)} chats from {csv_file_path} to {self.db_file_path}")
        except Exception as e:
            styler.error(f"Failed to migrate chats from CSV, will retry on next start: {e}")

    def saveChat(self, chat_id: int, username: str = "", first_name: str = "", last_name: str = "") -> bool:
        """
        Save a new chat

        Returns:
            bool: True if saved, False if the chat already exists or on error
        """
        try:
            with closing(self._connect()) as conn, conn:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO chats (chat_id, username, first_name, last_name, date_added) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (chat_id, username or '', first_name or '', last_name or '',
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )

            if cursor.rowcount == 0:
                styler.info(f"Chat ID {chat_id} already exists")
                return False

            styler.success(f"Chat ID {chat_id} saved successfully")
            return True
        except Exception as e:
            styler.error(f"Error saving chat ID: {e}")
            return False

    def getAllChatIds(self, show_partial: Optional[bool] = None, show_phases: Optional[bool] = None) -> List[int]:
        """Get IDs of all active chats, optionally only the ones with these settings"""
        conditions, params = ["is_active = 1"], []
        for column, value in (("show_partial", show_partial), ("show_phases", show_phases)):
            if value is not None:
                conditions.append(f"{column} = ?")
                params.append(value)

        try:
            with closing(self._connect()) as conn:
                rows = conn.execute(
                    f"SELECT chat_id FROM chats WHERE {' AND '.join(conditions)} ORDER BY chat_id", params
                ).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            styler.error(f"Error reading chat IDs: {e}")
            return []

    def get_chat_info(self, chat_id: int) -> Optional[ChatInfo]:
        """Get information for a specific chat ID"""
        try:
            with closing(self._connect()) as conn:
                row = conn.execute(
                    "SELECT chat_id, username, first_name, last_name, date_added, is_active, show_partial, show_phases "
                    "FROM chats WHERE chat_id = ?", (chat_id,)
                ).fetchone()
        except Exception as e:
            styler.error(f"Error reading chat info: {e}")
            return None

        if row is None:
            return None
        return ChatInfo(*row[:5], is_active=bool(row[5]), show_partial=bool(row[6]), show_phases=bool(row[7]))

    def deactivate_chat_id(self, chat_id: int) -> bool:
        """Mark a chat ID as inactive (soft delete)"""
        return self._set_active(chat_id, False)

    def activate_chat_id(self, chat_id: int) -> bool:
        """Mark a chat ID as active"""
        return self._set_active(chat_id, True)

    def set_show_partial(self, chat_id: int, show_partial: bool) -> bool:
        """Turn PARTIAL notifications on or off for a chat. Returns False if the chat is not subscribed"""
        return self._set_setting(chat_id, 'show_partial', show_partial)

    def set_show_phases(self, chat_id: int, show_phases: bool) -> bool:
        """Show or hide phase voltages in notifications for a chat. Returns False if the chat is not subscribed"""
        return self._set_setting(chat_id, 'show_phases', show_phases)

    def _set_setting(self, chat_id: int, column: str, value: bool) -> bool:
        if column not in CHAT_SETTINGS:  # column name goes into SQL text, never take it from outside
            raise ValueError(f"Unknown chat setting: {column}")
        try:
            with closing(self._connect()) as conn, conn:
                cursor = conn.execute(f"UPDATE chats SET {column} = ? WHERE chat_id = ?", (value, chat_id))

            if cursor.rowcount == 0:
                styler.warning(f"Chat ID {chat_id} not found")
                return False

            styler.success(f"Chat ID {chat_id} {column} = {value}")
            return True
        except Exception as e:
            styler.error(f"Error updating chat ID {chat_id}: {e}")
            return False

    def _set_active(self, chat_id: int, is_active: bool) -> bool:
        action = "activated" if is_active else "deactivated"
        try:
            with closing(self._connect()) as conn, conn:
                cursor = conn.execute("UPDATE chats SET is_active = ? WHERE chat_id = ?", (is_active, chat_id))

            if cursor.rowcount == 0:
                styler.warning(f"Chat ID {chat_id} not found")
                return False

            styler.success(f"Chat ID {chat_id} {action} successfully")
            return True
        except Exception as e:
            styler.error(f"Error updating chat ID {chat_id}: {e}")
            return False


# Create a singleton instance
storageService = StorageService()
