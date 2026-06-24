import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/minerbyner.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance REAL DEFAULT 1000000,
            ton_balance REAL DEFAULT 5,
            referrer_id INTEGER DEFAULT NULL,
            left_child INTEGER DEFAULT NULL,
            right_child INTEGER DEFAULT NULL,
            left_count INTEGER DEFAULT 0,
            right_count INTEGER DEFAULT 0,
            balance_milestone INTEGER DEFAULT 0,
            last_mine_time REAL DEFAULT 0,
            created_at REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id INTEGER,
            level INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        );
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            wallet TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS ton_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tx_hash TEXT UNIQUE,
            amount REAL,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS binary_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            milestone INTEGER,
            reward_trx REAL,
            reward_ton REAL DEFAULT 0,
            created_at REAL
        );
    """)
    # add new columns if not exist
    try:
        conn.execute("ALTER TABLE users ADD COLUMN left_child INTEGER DEFAULT NULL")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN right_child INTEGER DEFAULT NULL")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN left_count INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN right_count INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN balance_milestone INTEGER DEFAULT 0")
    except: pass
    conn.commit()
    conn.close()

def get_user(conn, uid):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def get_inventory(conn, uid):
    rows = conn.execute("SELECT item_id, level FROM inventory WHERE user_id=?", (uid,)).fetchall()
    return {str(r["item_id"]): r["level"] for r in rows}
