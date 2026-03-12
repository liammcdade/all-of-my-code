import sqlite3
import pandas as pd


class SQLProcessor:
    """SQL query processor with database connectivity."""
    
    def __init__(self, db_connection_string=None, db_type="sqlite"):
        """Initialize SQL processor."""
        self.db_connection_string = db_connection_string
        self.db_type = db_type.lower()
        self.connection = None

    def connect(self):
        """Establish database connection."""
        if self.connection:
            return

        if not self.db_connection_string:
            raise ValueError("Database connection string must be provided")

        if self.db_type == "sqlite":
            self.connection = sqlite3.connect(self.db_connection_string)
        else:
            raise NotImplementedError(f"Database type '{self.db_type}' not supported")

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, query: str, params=None, fetch_results=True):
        """Execute SQL query and return results."""
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())

            if fetch_results:
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return pd.DataFrame(results, columns=columns)
            else:
                self.connection.commit()
                return cursor.rowcount if cursor.rowcount != -1 else True
        finally:
            cursor.close()

    def execute_script(self, sql_script: str):
        """Execute multiple SQL statements."""
        if not self.connection:
            self.connect()
        
        self.connection.executescript(sql_script)
        self.connection.commit()
