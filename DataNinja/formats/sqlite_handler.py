import os
import sqlite3
import pandas as pd
try:
    from ..core.loader import DataLoader
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from core.loader import DataLoader


class SQLiteHandler(DataLoader):
    """Handles SQLite database loading and saving operations."""
    
    def _connect(self, connect_args=None):
        """Create SQLite connection."""
        return sqlite3.connect(self.source, **(connect_args or {}))

    def load_data(self, table_name=None, query=None, **kwargs):
        """Load data from SQLite database."""
        if not (table_name or query):
            raise ValueError("Either 'table_name' or 'query' must be provided")
        if table_name and query:
            raise ValueError("Provide either 'table_name' or 'query', not both")
        
        # Build SQL query
        if table_name:
            if not table_name.replace("_", "").isalnum():
                raise ValueError(f"Invalid table_name: '{table_name}'")
            sql = f"SELECT * FROM {table_name}"
        else:
            sql = query
        
        # Execute query
        connect_args = kwargs.pop("connect_args", {})
        with self._connect(connect_args) as conn:
            return pd.read_sql_query(sql, conn, **kwargs)

    def save_data(self, data, table_name, if_exists="fail", index=False, **kwargs):
        """Save DataFrame to SQLite database."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Data must be a pandas DataFrame")
        if not table_name or not isinstance(table_name, str):
            raise ValueError("table_name must be a non-empty string")
        
        # Create directory if needed
        db_dir = os.path.dirname(self.source)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Save data
        connect_args = kwargs.pop("connect_args", {})
        with self._connect(connect_args) as conn:
            data.to_sql(table_name, conn, if_exists=if_exists, index=index, **kwargs)


