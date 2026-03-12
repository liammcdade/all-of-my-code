import unittest
import os
import pandas as pd
from pandas.testing import assert_frame_equal
import sqlite3
import tempfile
import shutil
import logging  # For capturing log messages if needed

from DataNinja.formats.sqlite_handler import SQLiteHandler
from DataNinja.core.loader import DataLoader  # To test inheritance if needed


# Helper to capture log messages
class LogCaptureHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))

    def get_messages(self):
        return self.records


class TestSQLiteHandlerInitialization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "init_test.db")
        # SQLite creates the file on first connect, so it doesn't need to exist for init

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_initialization_valid_source(self):
        handler = SQLiteHandler(source=self.db_path)
        self.assertEqual(handler.source, self.db_path)
        self.assertIsInstance(handler.logger, logging.Logger)

    def test_get_source_info(self):
        handler = SQLiteHandler(source=self.db_path)
        self.assertEqual(handler.get_source_info(), f"Data source: {self.db_path}")

    def test_init_empty_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            SQLiteHandler(source="")

    def test_init_none_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            SQLiteHandler(source=None)


class TestSQLiteHandlerSaveAndLoadData(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_main.db")
        self.db_path_subdir = os.path.join(self.temp_dir, "sub", "test_sub.db")

        self.df1 = pd.DataFrame({"colA": [10, 20], "colB": ["alpha", "beta"]})
        self.df2 = pd.DataFrame({"colA": [30, 40], "colB": ["gamma", "delta"]})
        self.df3_other_schema = pd.DataFrame(
            {"colX": [1.1, 2.2], "colY": [True, False]}
        )

        # Configure a logger for the SQLiteHandler to capture its messages
        self.log_capture_handler = LogCaptureHandler()
        self.sqlite_handler_logger = logging.getLogger(
            "DataNinja.formats.sqlite_handler.SQLiteHandler"
        )
        self.sqlite_handler_logger.addHandler(self.log_capture_handler)
        self.sqlite_handler_logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.sqlite_handler_logger.removeHandler(self.log_capture_handler)
        # Attempt to close any open connections that might be lingering from failed tests
        # This is a bit of a hack; ideally, tests ensure connections are closed.
        # SQLite usually releases locks when Python exits, but explicit close is better.
        # Forcing garbage collection can sometimes help on Windows.
        import gc

        gc.collect()
        shutil.rmtree(self.temp_dir)

    # --- Save Data Tests ---
    def test_save_data_if_exists_fail_first_time(self):
        handler = SQLiteHandler(source=self.db_path)
        handler.save_data(self.df1, table_name="table1", if_exists="fail")
        loaded_df = handler.load_data(table_name="table1")
        assert_frame_equal(loaded_df, self.df1)

    def test_save_data_if_exists_fail_second_time_raises_valueerror(self):
        handler = SQLiteHandler(source=self.db_path)
        handler.save_data(self.df1, table_name="table1", if_exists="fail")  # First save
        # pandas to_sql with if_exists='fail' raises ValueError if table already exists
        with self.assertRaises(ValueError):
            handler.save_data(self.df2, table_name="table1", if_exists="fail")

    def test_save_data_if_exists_replace(self):
        handler = SQLiteHandler(source=self.db_path)
        handler.save_data(self.df1, table_name="table_replace", if_exists="fail")
        handler.save_data(self.df2, table_name="table_replace", if_exists="replace")
        loaded_df = handler.load_data(table_name="table_replace")
        assert_frame_equal(loaded_df, self.df2)

    def test_save_data_if_exists_append(self):
        handler = SQLiteHandler(source=self.db_path)
        handler.save_data(self.df1, table_name="table_append", if_exists="replace")
        handler.save_data(self.df2, table_name="table_append", if_exists="append")
        expected_df = pd.concat([self.df1, self.df2], ignore_index=True)
        loaded_df = handler.load_data(table_name="table_append")
        assert_frame_equal(loaded_df, expected_df)

    def test_save_data_with_index_true(self):
        handler = SQLiteHandler(source=self.db_path)
        df_custom_idx = self.df1.set_index(pd.Index(["idx1", "idx2"], name="MyIndex"))
        handler.save_data(
            df_custom_idx, table_name="table_idx_true", if_exists="replace", index=True
        )

        # Reload using pandas directly to check index
        conn = sqlite3.connect(self.db_path)
        reloaded_df = pd.read_sql_query(
            "SELECT * FROM table_idx_true", conn, index_col="MyIndex"
        )
        conn.close()
        assert_frame_equal(
            reloaded_df, df_custom_idx
        )  # df_custom_idx already has index

    def test_save_data_default_index_false(self):
        handler = SQLiteHandler(source=self.db_path)
        df_custom_idx = self.df1.set_index(pd.Index(["idx1", "idx2"], name="MyIndex"))
        # Save with default index=False
        handler.save_data(
            df_custom_idx, table_name="table_idx_false", if_exists="replace"
        )

        loaded_df = handler.load_data(table_name="table_idx_false")
        # Expect default 0-based index, original index 'MyIndex' becomes a regular column if not dropped
        # Pandas to_sql with index=False: If the DataFrame has a named index, that index will NOT be written.
        # So, loaded_df should not have 'MyIndex' as its index.
        self.assertNotIn(
            "MyIndex", loaded_df.columns
        )  # Check it's not a column if index=False
        self.assertNotEqual(loaded_df.index.name, "MyIndex")
        assert_frame_equal(
            loaded_df, self.df1.reset_index(drop=True)
        )  # Compare against original data without MyIndex

    def test_save_data_creates_subdirectory_for_db(self):
        handler = SQLiteHandler(source=self.db_path_subdir)
        self.assertFalse(
            os.path.exists(os.path.dirname(self.db_path_subdir))
        )  # Dir shouldn't exist yet
        handler.save_data(self.df1, table_name="sub_table")
        self.assertTrue(os.path.exists(self.db_path_subdir))
        loaded_df = handler.load_data(table_name="sub_table")
        assert_frame_equal(loaded_df, self.df1)

    def test_save_data_no_table_name_raises_valueerror(self):
        handler = SQLiteHandler(source=self.db_path)
        with self.assertRaisesRegex(
            ValueError, "'table_name' must be provided as a non-empty string."
        ):
            handler.save_data(self.df1, table_name=None)
        with self.assertRaisesRegex(
            ValueError, "'table_name' must be provided as a non-empty string."
        ):
            handler.save_data(self.df1, table_name="")

    def test_save_data_not_dataframe_raises_typeerror(self):
        handler = SQLiteHandler(source=self.db_path)
        with self.assertRaisesRegex(
            TypeError, "Data to save must be a pandas DataFrame."
        ):
            handler.save_data("this is not a DataFrame", table_name="bad_data_table")

    def test_save_empty_dataframe_if_exists_fail(self):
        handler = SQLiteHandler(source=self.db_path)
        empty_df = pd.DataFrame(
            {"A": pd.Series(dtype="int"), "B": pd.Series(dtype="object")}
        )
        # pandas to_sql with an empty DataFrame can raise ValueError if table doesn't exist
        # because it cannot infer SQL types. If table exists, it might do nothing or truncate.
        # Current handler catches this ValueError.
        with self.assertRaises(ValueError) as context:
            handler.save_data(empty_df, table_name="empty_df_table", if_exists="fail")
        self.assertTrue(
            "Cannot infer 'A' SQL type" in str(context.exception)
            or "Empty DataFrame" in str(context.exception)
        )

    # --- Load Data Tests ---
    def test_load_data_by_table_name(self):
        handler = SQLiteHandler(source=self.db_path)
        handler.save_data(
            self.df3_other_schema, table_name="load_test_table", if_exists="replace"
        )
        loaded_df = handler.load_data(table_name="load_test_table")
        assert_frame_equal(loaded_df, self.df3_other_schema)

    def test_load_data_by_query(self):
        handler = SQLiteHandler(source=self.db_path)
        handler.save_data(self.df1, table_name="query_load_table", if_exists="replace")
        handler.save_data(self.df2, table_name="query_load_table", if_exists="append")

        query = "SELECT * FROM query_load_table WHERE colA >= 30"
        loaded_df = handler.load_data(query=query)
        # df2 has colA [30, 40]
        assert_frame_equal(loaded_df, self.df2.reset_index(drop=True))

    def test_load_data_non_existent_table_raises_operationalerror(self):
        handler = SQLiteHandler(source=self.db_path)
        # Ensure DB file exists but table does not
        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            conn.close()

        with self.assertRaises((sqlite3.OperationalError, pd.errors.DatabaseError)):
            handler.load_data(table_name="table_does_not_exist_at_all")

    def test_load_data_invalid_sql_query_raises_operationalerror(self):
        handler = SQLiteHandler(source=self.db_path)
        if not os.path.exists(self.db_path):  # Ensure db exists for query test
            handler.save_data(self.df1, table_name="dummy_for_invalid_query")

        with self.assertRaises((sqlite3.OperationalError, pd.errors.DatabaseError)):
            handler.load_data(
                query="SELECT FROM NonExistentTable WHERE Invalid Syntax Here"
            )

    def test_load_data_no_table_name_or_query_raises_valueerror(self):
        handler = SQLiteHandler(source=self.db_path)
        with self.assertRaisesRegex(
            ValueError, "Either 'table_name' or 'query' must be provided."
        ):
            handler.load_data()

    def test_load_data_both_table_name_and_query_raises_valueerror(self):
        handler = SQLiteHandler(source=self.db_path)
        with self.assertRaisesRegex(
            ValueError, "Provide either 'table_name' or 'query', not both."
        ):
            handler.load_data(table_name="some_table", query="SELECT * FROM some_table")

    def test_load_data_from_empty_db_file_table_not_found(self):
        empty_db_file = os.path.join(self.temp_dir, "truly_empty.db")
        open(empty_db_file, "a").close()  # Creates a 0-byte file
        handler = SQLiteHandler(source=empty_db_file)

        # Loading from a 0-byte file (not a valid SQLite DB) will cause errors
        # when pandas/sqlite3 try to operate on it. Often "no such table" or "file is not a database".
        with self.assertRaises(
            (sqlite3.OperationalError, sqlite3.DatabaseError, pd.errors.DatabaseError)
        ):
            handler.load_data(table_name="any_table")


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
