import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("smart_agri.db")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM users")
    conn.commit()
    remaining = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    print("remaining_users:", remaining)
    conn.close()


if __name__ == "__main__":
    main()
