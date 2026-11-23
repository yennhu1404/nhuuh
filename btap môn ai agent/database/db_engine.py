import sqlite3
from typing import List, Dict, Any, Tuple
from config.settings import DB_PATH

class DWHDatabaseEngine:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_read_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Executes a secure read query and returns rows as dictionaries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_script(self, sql_script: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(sql_script)
            conn.commit()

