import sqlite3
import logging
from flask import g

logger = logging.getLogger('TitanDB')

class Database:
    def __init__(self, db_name):
        self.db_name = db_name

    def get_connection(self):
        conn = getattr(g, '_database', None)
        if conn is None:
            conn = g._database = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
        return conn

    def close_connection(self, exception):
        conn = getattr(g, '_database', None)
        if conn is not None:
            conn.close()

    def init_db(self):
        """Initialize schema with default data."""
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            # Users Table
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        role TEXT,
                        full_name TEXT,
                        api_key TEXT)''')
            
            # Shipments Table
            c.execute('''CREATE TABLE IF NOT EXISTS shipments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tracking_code TEXT UNIQUE,
                        user_id INTEGER,
                        status TEXT,
                        notes TEXT,
                        destination TEXT)''')
            
            # Logs Table
            c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT,
                        user_id INTEGER,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

            # Seed Data (MD5 Passwords)
            # admin / admin123
            c.execute("INSERT OR IGNORE INTO users (id, username, password, role, full_name, api_key) VALUES (1, 'admin', '0192023a7bbd73250516f069df18b500', 'admin', 'System Administrator', 'TITAN_ROOT_KEY')")
            # driver / driver
            c.execute("INSERT OR IGNORE INTO users (id, username, password, role, full_name, api_key) VALUES (2, 'driver', 'e2e015843a7b51e04193561a335017d8', 'driver', 'John Doe Driver', 'TITAN_DRV_001')")
            # client / client
            c.execute("INSERT OR IGNORE INTO users (id, username, password, role, full_name, api_key) VALUES (3, 'client', '62608e08adc29a8d6dbc9754e659f125', 'client', 'Alice Client', 'TITAN_CLT_002')")
            
            # Seed Shipments
            c.execute("INSERT OR IGNORE INTO shipments (id, tracking_code, user_id, status, notes, destination) VALUES (1001, 'TRK-99-XA', 3, 'IN_TRANSIT', 'Handle with care', 'New York, US')")
            c.execute("INSERT OR IGNORE INTO shipments (id, tracking_code, user_id, status, notes, destination) VALUES (1002, 'TRK-88-BB', 3, 'DELIVERED', 'Left at porch', 'London, UK')")
            c.execute("INSERT OR IGNORE INTO shipments (id, tracking_code, user_id, status, notes, destination) VALUES (1003, 'TRK-77-CC', 2, 'PENDING', 'Awaiting pickup', 'Berlin, DE')")
            
            conn.commit()
            logger.info("Database initialized successfully.")

    # --- QUERY METHODS ---

    def query_secure(self, query, args=(), one=False):
        """Safe execution using parameters."""
        cur = self.get_connection().execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv

    def execute_script_unsafe(self, query_script):
        try:
            cur = self.get_connection().executescript(query_script)
            self.get_connection().commit()
            return True
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return False

    def query_unsafe(self, query):
        try:
            logger.warning(f"Executing unsafe query: {query}")
            cur = self.get_connection().execute(query)
            rv = cur.fetchall()
            return rv
        except Exception as e:
            raise e 

# Initialize instance
db_instance = Database('titan_enterprise.db')
