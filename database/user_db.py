import os
import sqlite3
from datetime import datetime

from config import STORE_DB_PATH


class UserDatabase:
    def __init__(self, db_path=STORE_DB_PATH):
        self.db_path = db_path
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    avatar_path TEXT DEFAULT '',
                    recognize_count INTEGER NOT NULL DEFAULT 0,
                    last_recognize_date TEXT DEFAULT '',
                    nick_name TEXT DEFAULT '开心菜园阿伯',
                    signature TEXT DEFAULT '欢迎光临我的开心菜园！',
                    following_count INTEGER DEFAULT 0,
                    followers_count INTEGER DEFAULT 0,
                    share_count INTEGER DEFAULT 0
                )
                """
            )
            self._ensure_column(conn, "users", "nick_name", "TEXT DEFAULT '开心菜园阿伯'")
            self._ensure_column(conn, "users", "signature", "TEXT DEFAULT '欢迎光临我的开心菜园！'")
            self._ensure_column(conn, "users", "following_count", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "users", "followers_count", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "users", "share_count", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "users", "gender", "TEXT DEFAULT '未设置'")
            self._ensure_column(conn, "users", "phone", "TEXT DEFAULT ''")
            self._ensure_column(conn, "users", "region", "TEXT DEFAULT ''")
            self._ensure_column(conn, "users", "main_crop", "TEXT DEFAULT ''")
            self._ensure_column(conn, "users", "birth_date", "TEXT DEFAULT ''")
            # Repair profiles written by older builds that decoded UTF-8 text
            # with the wrong Windows code page.
            conn.execute(
                "UPDATE users SET nick_name = username "
                "WHERE nick_name IS NULL OR nick_name = '' OR nick_name LIKE '%�%'"
            )
            conn.execute(
                "UPDATE users SET signature = '欢迎来到我的智慧农场' "
                "WHERE signature IS NULL OR signature = '' OR signature LIKE '%�%'"
            )
            conn.commit()

    @staticmethod
    def _ensure_column(conn, table_name, column_name, column_def):
        columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

    @staticmethod
    def _row_to_user(row):
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "password": row["password"],
            "role": row["role"],
            "avatar_path": row["avatar_path"] or "",
            "recognize_count": int(row["recognize_count"]),
            "last_recognize_date": row["last_recognize_date"] or "",
            "nick_name": row["nick_name"] or "开心菜园阿伯",
            "signature": row["signature"] or "欢迎光临我的开心菜园！",
            "following_count": int(row["following_count"] or 0),
            "followers_count": int(row["followers_count"] or 0),
            "share_count": int(row["share_count"] or 0),
            "gender": row["gender"] or "未设置",
            "phone": row["phone"] or "",
            "region": row["region"] or "",
            "main_crop": row["main_crop"] or "",
            "birth_date": row["birth_date"] or "",
        }

    def get_user(self, username):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        return self._row_to_user(row)

    def authenticate_user(self, username, password):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()
        return self._row_to_user(row)

    def username_exists(self, username):
        return self.get_user(username) is not None

    def create_user(self, username, password, role, avatar_path=""):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username, password, role, avatar_path, recognize_count, last_recognize_date,
                    nick_name, signature, following_count, followers_count, share_count
                ) VALUES (?, ?, ?, ?, 0, '', ?, '欢迎光临我的开心菜园！', 0, 0, 0)
                """,
                (username, password, role, avatar_path, username),
            )
            conn.commit()
        return self.get_user(username)

    def reset_users(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM users")
            conn.commit()

    def update_profile(self, username, nick_name=None, signature=None):
        user = self.get_user(username)
        if not user:
            return None
        nick_name = nick_name if nick_name is not None else user["nick_name"]
        signature = signature if signature is not None else user["signature"]
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET nick_name = ?, signature = ? WHERE username = ?",
                (nick_name, signature, username),
            )
            conn.commit()
        return self.get_user(username)

    def update_profile_details(self, username, **values):
        """Update editable profile fields while keeping account identity immutable."""
        allowed = {
            "nick_name", "signature", "gender", "phone", "region",
            "main_crop", "birth_date",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates or not self.get_user(username):
            return self.get_user(username)
        assignments = ", ".join(f"{key} = ?" for key in updates)
        parameters = list(updates.values()) + [username]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE users SET {assignments} WHERE username = ?", parameters
            )
            conn.commit()
        return self.get_user(username)

    def update_avatar(self, username, avatar_path):
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET avatar_path = ? WHERE username = ?",
                (avatar_path, username),
            )
            conn.commit()

    def reset_daily_recognize_if_needed(self, username):
        today = datetime.now().strftime("%Y-%m-%d")
        user = self.get_user(username)
        if not user:
            return None
        if user["last_recognize_date"] != today:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET recognize_count = 0, last_recognize_date = ? WHERE username = ?",
                    (today, username),
                )
                conn.commit()
            user = self.get_user(username)
        return user

    def can_recognize_today(self, username):
        user = self.reset_daily_recognize_if_needed(username)
        if not user:
            return False, None
        if user["role"] == "vip":
            return True, user
        return user["recognize_count"] < 3, user

    def increase_recognize_count(self, username):
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET recognize_count = recognize_count + 1, last_recognize_date = ? WHERE username = ?",
                (today, username),
            )
            conn.commit()
        return self.get_user(username)


USER_DB = UserDatabase()
