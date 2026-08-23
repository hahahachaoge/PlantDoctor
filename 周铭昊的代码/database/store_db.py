import os
import sqlite3
from datetime import datetime, timedelta

from kivy.app import App

from config import STORE_DB_PATH, STORE_CATALOG_VERSION, STORE_PRODUCTS_SEED, ALL_PEST_ENTRIES, DEFAULT_COMMENT_USER, PESTICIDE_ENTRIES


class StoreDatabase:
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS store_products (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                    sub_category TEXT, specification TEXT NOT NULL, price REAL NOT NULL,
                    sold_count INTEGER NOT NULL DEFAULT 0, stock INTEGER NOT NULL DEFAULT 0,
                    image TEXT, description TEXT,
                    is_hot INTEGER NOT NULL DEFAULT 0, is_featured INTEGER NOT NULL DEFAULT 0
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS store_favorites (
                    username TEXT NOT NULL, product_id INTEGER NOT NULL,
                    PRIMARY KEY (username, product_id)
                )""")
            favorite_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(store_favorites)").fetchall()
            }
            if favorite_columns != {"username", "product_id"}:
                conn.execute("DROP TABLE IF EXISTS store_favorites_legacy")
                conn.execute("ALTER TABLE store_favorites RENAME TO store_favorites_legacy")
                conn.execute("""
                    CREATE TABLE store_favorites (
                        username TEXT NOT NULL, product_id INTEGER NOT NULL,
                        PRIMARY KEY (username, product_id)
                    )""")
                legacy_columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(store_favorites_legacy)").fetchall()
                }
                if {"username", "product_id"}.issubset(legacy_columns):
                    conn.execute("""
                        INSERT OR IGNORE INTO store_favorites (username, product_id)
                        SELECT username, product_id FROM store_favorites_legacy
                    """)
                conn.execute("DROP TABLE store_favorites_legacy")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS store_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
                    username TEXT NOT NULL, comment TEXT NOT NULL,
                    comment_date TEXT NOT NULL, created_at TEXT NOT NULL
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS community_likes (
                    username TEXT NOT NULL, post_id INTEGER NOT NULL,
                    PRIMARY KEY (username, post_id)
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS community_post_stats (
                    post_key TEXT PRIMARY KEY, view_count INTEGER NOT NULL DEFAULT 0
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS community_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, post_key TEXT NOT NULL,
                    username TEXT NOT NULL, comment TEXT NOT NULL,
                    comment_date TEXT NOT NULL, created_at TEXT NOT NULL
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS store_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
                    product_id INTEGER NOT NULL, order_date TEXT NOT NULL,
                    delivery_date TEXT NOT NULL, created_at TEXT NOT NULL
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pest_entries (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                    intro TEXT NOT NULL, treatment TEXT NOT NULL
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_pest_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT,
                    pest_name TEXT, latitude REAL, longitude REAL, created_at TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_meta (
                    meta_key TEXT PRIMARY KEY, meta_value TEXT
                )""")
            version_row = conn.execute(
                "SELECT meta_value FROM app_meta WHERE meta_key = 'store_catalog_version'"
            ).fetchone()
            current_version = version_row["meta_value"] if version_row else None
            if current_version != STORE_CATALOG_VERSION:
                conn.execute("DELETE FROM store_products")
                conn.execute("DELETE FROM store_favorites")
                conn.execute("DELETE FROM pest_entries")
                conn.executemany("""
                    INSERT INTO store_products (
                        id, name, category, sub_category, specification, price, sold_count,
                        stock, image, description, is_hot, is_featured
                    ) VALUES (
                        :id, :name, :category, :sub_category, :specification, :price, :sold_count,
                        :stock, :image, :description, :is_hot, :is_featured
                    )""", STORE_PRODUCTS_SEED)
                conn.executemany(
                    "INSERT INTO pest_entries (id, name, intro, treatment) VALUES (:id, :name, :intro, :treatment)",
                    ALL_PEST_ENTRIES,
                )
                conn.execute(
                    "INSERT OR REPLACE INTO app_meta (meta_key, meta_value) VALUES ('store_catalog_version', ?)",
                    (STORE_CATALOG_VERSION,),
                )
            conn.execute("UPDATE store_products SET sold_count = 0")
            conn.execute("UPDATE store_products SET category = '精选好物', sub_category = '精选' WHERE id IN (2001, 2002, 2003, 2004, 2005)")
            conn.execute("UPDATE store_products SET category = '热销榜单', sub_category = '热销' WHERE id IN (2101, 2102, 2103, 2104, 2105)")
            conn.execute("UPDATE store_products SET category = '肥料', sub_category = '肥料' WHERE id IN (2201, 2202, 2203, 2204, 2205, 2206)")
            conn.execute("UPDATE store_products SET category = '杀虫剂', sub_category = '杀虫剂' WHERE id IN (2301, 2302, 2303, 2304, 2305, 2306)")
            conn.execute("UPDATE store_products SET category = '商城首页', sub_category = '广告' WHERE id = 2401")
            conn.execute("UPDATE store_products SET category = '热销榜单', sub_category = '热销榜单' WHERE id IN (2402, 2403, 2404, 2405)")
            conn.execute("UPDATE store_products SET category = '肥料', sub_category = '肥料推荐' WHERE id IN (2406, 2407)")
            conn.execute("UPDATE store_products SET category = '杀虫剂', sub_category = '杀虫剂推荐' WHERE id IN (2408, 2409)")
            conn.commit()

    @staticmethod
    def _row_to_product(row):
        return {
            "id": row["id"], "name": row["name"], "category": row["category"],
            "sub_category": row["sub_category"] or "", "specification": row["specification"],
            "price": float(row["price"]), "sold_count": int(row["sold_count"]),
            "stock": int(row["stock"]), "image": row["image"] or "",
            "description": row["description"] or "",
            "is_hot": bool(row["is_hot"]), "is_featured": bool(row["is_featured"]),
        }

    @staticmethod
    def _normalize_product_name(name):
        if not name:
            return ""
        aliases = {
            "高效氯氟氰菊酯": "高效氯氟氰菊酯",
            "吡虫啉": "吡虫啉",
            "阿维菌素": "阿维菌素",
            "硫酸钾复合肥": "硫酸钾复合肥",
        }
        return aliases.get(name, name)

    def _canonicalize_row(self, conn, row):
        if not row:
            return None
        name = row["name"]
        canonical = conn.execute(
            """SELECT * FROM store_products WHERE name = ?
               ORDER BY CASE WHEN category = '商城首页' THEN 1 ELSE 0 END, sold_count DESC, id
               LIMIT 1""",
            (name,),
        ).fetchone()
        return canonical or row

    def get_products_by_tab(self, tab_name):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM store_products WHERE category = ? ORDER BY id", (tab_name,)
            ).fetchall()
        seen = set()
        products = []
        with self._connect() as conn:
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def get_product(self, product_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?", (product_id,)
            ).fetchone()
            row = self._canonicalize_row(conn, row)
        return self._row_to_product(row) if row else None

    def increment_sold_count(self, product_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?", (product_id,)
            ).fetchone()
            row = self._canonicalize_row(conn, row)
            if not row:
                return None
            conn.execute(
                "UPDATE store_products SET sold_count = sold_count + 1 WHERE id = ?", (row["id"],)
            )
            conn.commit()
        return self.get_product(row["id"])

    def is_favorite(self, product_id):
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?", (product_id,)
            ).fetchone()
            row = self._canonicalize_row(conn, row)
            canonical_id = row["id"] if row else product_id
            row = conn.execute(
                "SELECT 1 FROM store_favorites WHERE username = ? AND product_id = ?",
                (username, canonical_id),
            ).fetchone()
        return bool(row)

    def toggle_favorite(self, product_id):
        app = App.get_running_app()
        username = app.current_user["username"] if app and app.current_user else ""
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM store_products WHERE id = ?", (product_id,)
            ).fetchone()
            row = self._canonicalize_row(conn, row)
            canonical_id = row["id"] if row else product_id
            existing = conn.execute(
                "SELECT 1 FROM store_favorites WHERE username = ? AND product_id = ?",
                (username, canonical_id),
            ).fetchone()
            if existing:
                conn.execute(
                    "DELETE FROM store_favorites WHERE username = ? AND product_id = ?",
                    (username, canonical_id),
                )
                conn.commit()
                return False
            conn.execute(
                "INSERT OR REPLACE INTO store_favorites (username, product_id) VALUES (?, ?)",
                (username, canonical_id),
            )
            conn.commit()
            return True

    def get_comments(self, product_id):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT username, comment, comment_date FROM store_comments WHERE product_id = ? ORDER BY id DESC",
                (product_id,),
            ).fetchall()
        return [{"username": r["username"], "comment": r["comment"], "comment_date": r["comment_date"]} for r in rows]

    def add_comment(self, product_id, comment_text, username=DEFAULT_COMMENT_USER):
        today = datetime.now().strftime("%Y-%m-%d")
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO store_comments (product_id, username, comment, comment_date, created_at) VALUES (?, ?, ?, ?, ?)",
                (product_id, username, comment_text, today, created_at),
            )
            conn.commit()
        return {"username": username, "comment": comment_text, "comment_date": today}

    def get_favorite_products(self, username):
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT p.* FROM store_products p
                   INNER JOIN store_favorites f ON p.id = f.product_id
                   WHERE f.username = ? ORDER BY p.id""",
                (username,),
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def get_products_by_ids(self, product_ids):
        if not product_ids:
            return []
        placeholders = ",".join("?" for _ in product_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM store_products WHERE id IN ({placeholders}) ORDER BY id",
                tuple(product_ids),
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def search_products(self, keyword):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM store_products WHERE name LIKE ? ORDER BY id", (f"%{keyword}%",)
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def get_products_for_home(self, sub_category):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM store_products WHERE sub_category = ? ORDER BY id", (sub_category,)
            ).fetchall()
            seen = set()
            products = []
            for row in rows:
                product = self._row_to_product(self._canonicalize_row(conn, row))
                key = self._normalize_product_name(product["name"])
                if key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def toggle_post_like(self, username, post_id):
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM community_likes WHERE username = ? AND post_id = ?",
                (username, post_id),
            ).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM community_likes WHERE username = ? AND post_id = ?",
                    (username, post_id),
                )
                conn.commit()
                return False
            conn.execute(
                "INSERT INTO community_likes (username, post_id) VALUES (?, ?)",
                (username, post_id),
            )
            conn.commit()
            return True

    def has_liked_post(self, username, post_id):
        if not username:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM community_likes WHERE username = ? AND post_id = ?",
                (username, post_id),
            ).fetchone()
        return bool(row)

    def get_post_like_count(self, post_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM community_likes WHERE post_id = ?", (post_id,)
            ).fetchone()
        return int(row["count"]) if row else 0

    def increment_post_view(self, post_key):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO community_post_stats (post_key, view_count) VALUES (?, 1)
                   ON CONFLICT(post_key) DO UPDATE SET view_count = view_count + 1""",
                (post_key,),
            )
            conn.commit()
            row = conn.execute(
                "SELECT view_count FROM community_post_stats WHERE post_key = ?", (post_key,)
            ).fetchone()
        return int(row["view_count"]) if row else 0

    def get_post_view_count(self, post_key):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT view_count FROM community_post_stats WHERE post_key = ?", (post_key,)
            ).fetchone()
        return int(row["view_count"]) if row else 0

    def get_post_comments(self, post_key):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT username, comment, comment_date FROM community_comments WHERE post_key = ? ORDER BY id DESC",
                (post_key,),
            ).fetchall()
        return [{"username": r["username"], "comment": r["comment"], "comment_date": r["comment_date"]} for r in rows]

    def add_post_comment(self, post_key, comment_text, username):
        today = datetime.now().strftime("%Y-%m-%d")
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO community_comments (post_key, username, comment, comment_date, created_at) VALUES (?, ?, ?, ?, ?)",
                (post_key, username, comment_text, today, created_at),
            )
            conn.commit()
        return {"username": username, "comment": comment_text, "comment_date": today}

    def add_order(self, username, product_id):
        order_dt = datetime.now()
        delivery_dt = order_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=3)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO store_orders (username, product_id, order_date, delivery_date, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, product_id, order_dt.strftime("%Y-%m-%d"),
                 delivery_dt.strftime("%Y-%m-%d"), order_dt.isoformat()),
            )
            conn.commit()

    def get_orders(self, username):
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT o.id, o.product_id, o.order_date, o.delivery_date, o.created_at, p.*
                   FROM store_orders o
                   INNER JOIN store_products p ON p.id = o.product_id
                   WHERE o.username = ?
                   ORDER BY o.created_at DESC, o.id DESC""",
                (username,),
            ).fetchall()
        orders = []
        for row in rows:
            product = self._row_to_product(row)
            orders.append({
                "id": row["id"], "product_id": product["id"],
                "name": product["name"], "specification": product["specification"],
                "price": product["price"], "order_date": row["order_date"],
                "delivery_date": row["delivery_date"], "created_at": row["created_at"],
            })
        return orders

    def get_pest_entries(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM pest_entries ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def get_pest_entry(self, pest_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM pest_entries WHERE id = ?", (pest_id,)).fetchone()
        return dict(row) if row else None

    def get_pesticide_entries(self):
        return PESTICIDE_ENTRIES

    def get_pesticide_entry(self, pesticide_id):
        for entry in PESTICIDE_ENTRIES:
            if entry["id"] == pesticide_id:
                return entry
        return None

    def search_pesticides(self, keyword):
        keyword_lower = keyword.lower()
        return [
            p for p in PESTICIDE_ENTRIES
            if keyword_lower in p["name"].lower()
            or keyword_lower in p["type"].lower()
            or keyword_lower in p["crops"].lower()
            or keyword_lower in p["target"].lower()
        ]

    def get_pesticide_entry_by_name(self, name):
        if not name:
            return None
        # 精确匹配
        for entry in PESTICIDE_ENTRIES:
            if entry["name"] == name:
                return entry
        # 模糊匹配
        for entry in PESTICIDE_ENTRIES:
            if entry["name"] in name or name in entry["name"]:
                return entry
        return None

    def get_fertilizer_entries(self):
        from config import ALL_FERTILIZER_ENTRIES
        return ALL_FERTILIZER_ENTRIES

    def get_fertilizer_entry(self, fertilizer_id):
        from config import ALL_FERTILIZER_ENTRIES
        for entry in ALL_FERTILIZER_ENTRIES:
            if entry["id"] == fertilizer_id:
                return entry
        return None

    def search_fertilizers(self, keyword):
        from config import ALL_FERTILIZER_ENTRIES
        keyword_lower = keyword.lower()
        return [
            f for f in ALL_FERTILIZER_ENTRIES
            if keyword_lower in f["name"].lower()
            or keyword_lower in f["type"].lower()
            or keyword_lower in f["crops"].lower()
        ]



STORE_DB = StoreDatabase()

