import unittest
import pandas as pd
import numpy as np
from DataNinja.core.cleaner import DataCleaner
from pandas.testing import assert_frame_equal, assert_series_equal
import io
import sys


# Helper to capture print outputs for logging checks if necessary
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = io.StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


class TestCleanerInitialization(unittest.TestCase):
    def test_init_with_dataframe(self):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        cleaner = DataCleaner(data=df)
        assert_frame_equal(cleaner.data, df)
        self.assertIsInstance(cleaner.get_cleaned_data(), pd.DataFrame)

    def test_init_with_list_of_lists_with_header(self):
        data_lol = [["A", "B"], [1, 3], [2, 4]]
        expected_df = pd.DataFrame([[1, 3], [2, 4]], columns=["A", "B"])
        cleaner = DataCleaner(data=data_lol)
        assert_frame_equal(cleaner.data, expected_df)

    def test_init_with_list_of_lists_without_header(self):
        # Pandas infers numeric headers 0, 1, ...
        data_lol = [[1, 3], [2, 4]]
        expected_df = pd.DataFrame([[1, 3], [2, 4]])
        cleaner = DataCleaner(data=data_lol)
        assert_frame_equal(cleaner.data, expected_df)

    def test_init_with_empty_list(self):
        # An empty list results in an empty DataFrame
        cleaner = DataCleaner(data=[])
        self.assertTrue(cleaner.data.empty)
        self.assertIsInstance(cleaner.data, pd.DataFrame)

    def test_init_with_list_of_empty_lists_header_only(self):
        # List of lists where first list is header, but no data rows
        data_lol = [["A", "B"]]
        expected_df = pd.DataFrame(columns=["A", "B"])
        cleaner = DataCleaner(data=data_lol)
        assert_frame_equal(cleaner.data, expected_df)

    def test_init_with_list_of_lists_malformed(self):
        # Test with a list that cannot easily be converted (e.g. mixed types not in tabular form)
        # The current implementation prints a warning and stores data as is.
        data_non_tabular = [1, "test", [2, 3]]
        with Capturing() as output:  # Capture print output
            cleaner = DataCleaner(data=data_non_tabular)
        self.assertIn("Warning: Could not convert input list to DataFrame", output[0])
        self.assertEqual(cleaner.data, data_non_tabular)

    def test_init_with_none(self):
        with self.assertRaises(ValueError):
            DataCleaner(data=None)

    def test_init_with_unsupported_type(self):
        with self.assertRaises(TypeError):
            DataCleaner(data="this is a string")
        with self.assertRaises(TypeError):
            DataCleaner(data=123)


class TestRemoveMissingValues(unittest.TestCase):
    def setUp(self):
        self.data_with_nan = pd.DataFrame(
            {
                "A": [1, 2, np.nan, 4, 5],
                "B": ["x", np.nan, "y", "z", "k"],
                "C": [10.0, 20.0, 30.0, np.nan, 50.0],
                "D": [True, False, True, False, True],  # No NaNs
            }
        )
        # Note: DataCleaner itself is not stateful for individual methods like remove_missing_values
        # It takes a df and returns a df. So, we don't strictly need self.cleaner here
        # but can instantiate it if we want to test it as part of a cleaner object.
        # For direct method testing, we can just call DataCleaner(some_df).method(some_df, ...)
        # However, to keep structure consistent with prompt, self.cleaner is initialized.
        self.cleaner_instance = DataCleaner(self.data_with_nan.copy())

    def test_drop_rows_default_any_na(self):
        # Operates on a copy passed to the method
        cleaned_df = self.cleaner_instance.remove_missing_values(
            self.data_with_nan.copy()
        )
        expected_df = self.data_with_nan.dropna(axis=0)  # Default for dropna
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_drop_rows_with_subset(self):
        # Remove rows if NA is in column 'B' or 'C'
        cleaned_df = self.cleaner_instance.remove_missing_values(
            self.data_with_nan.copy(), subset=["B", "C"]
        )
        expected_df = self.data_with_nan.dropna(subset=["B", "C"])
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_drop_rows_with_threshold(self):
        # Keep rows with at least 3 non-NA values
        # Row 2: (nan, y, 30.0, True) -> 3 non-NA
        # Row 3: (4, z, nan, False) -> 3 non-NA
        cleaned_df = self.cleaner_instance.remove_missing_values(
            self.data_with_nan.copy(), threshold=3
        )
        expected_df = self.data_with_nan.dropna(thresh=3)
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_drop_cols_strategy(self):
        df_with_nan_col = self.data_with_nan.copy()
        df_with_nan_col["E"] = np.nan  # All NaN column
        cleaned_df = self.cleaner_instance.remove_missing_values(
            df_with_nan_col, strategy="drop_cols"
        )
        expected_df = df_with_nan_col.dropna(axis=1)
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_no_missing_values(self):
        df_no_nan = pd.DataFrame({"X": [1, 2], "Y": ["a", "b"]})
        cleaned_df = self.cleaner_instance.remove_missing_values(df_no_nan.copy())
        assert_frame_equal(cleaned_df, df_no_nan)

    def test_empty_dataframe(self):
        df_empty = pd.DataFrame()
        cleaned_df = self.cleaner_instance.remove_missing_values(df_empty.copy())
        self.assertTrue(cleaned_df.empty)

    def test_unsupported_strategy(self):
        with Capturing() as output:
            cleaned_df = self.cleaner_instance.remove_missing_values(
                self.data_with_nan.copy(), strategy="unknown_strategy"
            )
        self.assertIn("Warning: Unknown strategy 'unknown_strategy'", output[0])
        assert_frame_equal(cleaned_df, self.data_with_nan)  # Should return original df

    def test_non_dataframe_input(self):
        # Instantiate a dummy cleaner to call the method
        dummy_cleaner = DataCleaner(pd.DataFrame())
        with Capturing() as output:
            result = dummy_cleaner.remove_missing_values("not a dataframe")
        self.assertEqual(result, "not a dataframe")
        self.assertIn(
            "Data is not a DataFrame. Cannot remove missing values effectively.",
            output[0],
        )


class TestConvertColumnType(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "A": ["1", "2", "3", "4"],
                "B": ["10.1", "20.2", "30.3", "40.4"],
                "C": ["apple", "banana", "cherry", "date"],
                "D": [True, False, True, False],
                "E": ["5", "not_a_number", "7", "8"],
            }
        )
        self.cleaner_instance = DataCleaner(self.df.copy())

    def test_convert_to_int(self):
        cleaned_df = self.cleaner_instance.convert_column_type(self.df.copy(), "A", int)
        self.assertEqual(
            cleaned_df["A"].dtype, np.int64
        )  # Or np.int32 depending on system
        assert_series_equal(
            cleaned_df["A"], pd.Series([1, 2, 3, 4], name="A", dtype=np.int64)
        )

    def test_convert_to_float(self):
        cleaned_df = self.cleaner_instance.convert_column_type(
            self.df.copy(), "B", float
        )
        self.assertEqual(cleaned_df["B"].dtype, np.float64)
        assert_series_equal(
            cleaned_df["B"],
            pd.Series([10.1, 20.2, 30.3, 40.4], name="B", dtype=np.float64),
        )

    def test_convert_to_str(self):
        # Convert 'D' (boolean) to string
        cleaned_df = self.cleaner_instance.convert_column_type(self.df.copy(), "D", str)
        self.assertEqual(cleaned_df["D"].dtype, object)  # String type
        assert_series_equal(
            cleaned_df["D"], pd.Series(["True", "False", "True", "False"], name="D")
        )

    def test_convert_non_convertible_value_error_caught(self):
        # Column 'E' has 'not_a_number'
        with Capturing() as output:  # Capture print output from the method
            cleaned_df = self.cleaner_instance.convert_column_type(
                self.df.copy(), "E", int
            )
        # The method catches the error and prints a message. The column remains unchanged.
        self.assertTrue(
            any(
                "Error converting column 'E' to <class 'int'>" in line
                for line in output
            )
        )
        assert_series_equal(cleaned_df["E"], self.df["E"])

    def test_convert_non_existent_column(self):
        with Capturing() as output:  # Capture print output
            cleaned_df = self.cleaner_instance.convert_column_type(
                self.df.copy(), "Z", int
            )
        self.assertIn(
            "Warning: Column 'Z' not found in DataFrame. Skipping type conversion.",
            output[0],
        )
        assert_frame_equal(cleaned_df, self.df)  # DataFrame should be unchanged

    def test_empty_dataframe(self):
        df_empty = pd.DataFrame(
            {"X": pd.Series([], dtype=object)}
        )  # Empty series with object type
        cleaned_df = self.cleaner_instance.convert_column_type(
            df_empty.copy(), "X", int
        )
        # Converting empty object series to int results in int64 empty series
        self.assertTrue(cleaned_df["X"].dtype == np.int64)
        self.assertTrue(cleaned_df["X"].empty)

        df_empty_no_cols = pd.DataFrame()
        with Capturing() as output:
            cleaned_df_no_cols = self.cleaner_instance.convert_column_type(
                df_empty_no_cols.copy(), "X", int
            )
        self.assertIn(
            "Warning: Column 'X' not found in DataFrame. Skipping type conversion.",
            output[0],
        )

    def test_non_dataframe_input(self):
        dummy_cleaner = DataCleaner(pd.DataFrame())
        with Capturing() as output:
            result = dummy_cleaner.convert_column_type("not a dataframe", "col", int)
        self.assertEqual(result, "not a dataframe")
        self.assertIn("Data is not a DataFrame. Cannot convert column type.", output[0])


class TestRemoveDuplicates(unittest.TestCase):
    def setUp(self):
        self.data_with_duplicates = pd.DataFrame(
            {
                "A": [1, 1, 2, 3, 2, 1],
                "B": ["x", "x", "y", "z", "y", "x"],
                "C": [10, 10, 20, 30, 20, 10],
            }
        )
        self.cleaner_instance = DataCleaner(self.data_with_duplicates.copy())

    def test_remove_duplicates_default_keep_first(self):
        cleaned_df = self.cleaner_instance.remove_duplicates(
            self.data_with_duplicates.copy()
        )
        expected_df = self.data_with_duplicates.drop_duplicates(keep="first")
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_remove_duplicates_keep_last(self):
        cleaned_df = self.cleaner_instance.remove_duplicates(
            self.data_with_duplicates.copy(), keep="last"
        )
        expected_df = self.data_with_duplicates.drop_duplicates(keep="last")
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_remove_duplicates_keep_false(self):
        # Drops all occurrences of duplicates
        cleaned_df = self.cleaner_instance.remove_duplicates(
            self.data_with_duplicates.copy(), keep=False
        )
        expected_df = self.data_with_duplicates.drop_duplicates(keep=False)
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_remove_duplicates_with_subset(self):
        # Consider duplicates based on columns 'A' and 'B' only
        cleaned_df = self.cleaner_instance.remove_duplicates(
            self.data_with_duplicates.copy(), subset=["A", "B"]
        )
        expected_df = self.data_with_duplicates.drop_duplicates(
            subset=["A", "B"], keep="first"
        )
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_df.reset_index(drop=True)
        )

    def test_no_duplicates(self):
        df_no_duplicates = pd.DataFrame({"X": [1, 2, 3], "Y": ["a", "b", "c"]})
        cleaned_df = self.cleaner_instance.remove_duplicates(df_no_duplicates.copy())
        assert_frame_equal(cleaned_df, df_no_duplicates)

    def test_empty_dataframe(self):
        df_empty = pd.DataFrame()
        cleaned_df = self.cleaner_instance.remove_duplicates(df_empty.copy())
        self.assertTrue(cleaned_df.empty)

    def test_non_dataframe_input(self):
        dummy_cleaner = DataCleaner(pd.DataFrame())
        with Capturing() as output:
            result = dummy_cleaner.remove_duplicates("not a dataframe")
        self.assertEqual(result, "not a dataframe")
        self.assertIn("Data is not a DataFrame. Cannot remove duplicates.", output[0])


class TestCleanDataOrchestration(unittest.TestCase):
    def setUp(self):
        self.initial_data = pd.DataFrame(
            {
                "ID": [1, 2, 3, 4, 5, 5],
                "Name": ["Alice", "Bob", "Charles", "David", "Eve", "Eve"],
                "Age": ["28", "35", np.nan, "22", "30", "30"],
                "Salary": [50000, 60000, 70000, "N/A", 80000, 80000],
                "City": ["NY", "LA", "CH", "NY", "LA", "LA"],
            }
        )
        # self.cleaner will be instantiated in each test to ensure fresh state

    def test_clean_data_multiple_operations(self):
        cleaner = DataCleaner(self.initial_data.copy())
        operations = [
            {"method": "remove_missing_values", "params": {"subset": ["Age"]}},
            {
                "method": "convert_column_type",
                "params": {"column": "Age", "new_type": float},
            },
            # Note: Salary 'N/A' will cause issues if trying to convert to numeric without prior handling.
            # The convert_column_type method currently logs an error and returns the df with the column unchanged.
            {
                "method": "convert_column_type",
                "params": {"column": "Salary", "new_type": float},
            },  # This will log error for 'N/A'
            {
                "method": "remove_duplicates",
                "params": {"subset": ["ID", "Name"], "keep": "first"},
            },
        ]

        # Manual calculation of expected result:
        # 1. remove_missing_values(subset=['Age'])
        df_step1 = self.initial_data.dropna(subset=["Age"]).reset_index(drop=True)
        # 2. convert_column_type(column='Age', new_type=float)
        df_step2 = df_step1.copy()
        df_step2["Age"] = df_step2["Age"].astype(float)
        # 3. convert_column_type(column='Salary', new_type=float) -> This will fail for 'N/A' and leave column as is.
        df_step3 = df_step2.copy()
        # The actual method tries conversion, logs error, original 'Salary' column is kept.
        # So df_step3['Salary'] is still object type with 'N/A'.

        # 4. remove_duplicates(subset=['ID', 'Name'], keep='first')
        expected_final_df = df_step3.drop_duplicates(
            subset=["ID", "Name"], keep="first"
        ).reset_index(drop=True)

        with Capturing() as output:  # Capture prints
            cleaner.clean_data(operations=operations)
        cleaned_df = cleaner.get_cleaned_data()

        self.assertTrue(
            any(
                "Error converting column 'Salary' to <class 'float'>" in line
                for line in output
            )
        )
        assert_frame_equal(
            cleaned_df.reset_index(drop=True), expected_final_df.reset_index(drop=True)
        )

    def test_clean_data_empty_operations_list(self):
        cleaner = DataCleaner(self.initial_data.copy())
        original_df = cleaner.data.copy()
        with Capturing() as output:
            cleaner.clean_data(operations=[])
        cleaned_df = cleaner.get_cleaned_data()
        self.assertIn(
            "No specific cleaning operations provided. Applying default steps (if any).",
            output[0],
        )
        assert_frame_equal(
            cleaned_df, original_df
        )  # self.data is updated with the copy from start of clean_data

    def test_clean_data_unknown_method(self):
        cleaner = DataCleaner(self.initial_data.copy())
        operations = [{"method": "non_existent_method", "params": {}}]
        original_df = cleaner.data.copy()
        with Capturing() as output:
            cleaner.clean_data(operations=operations)
        cleaned_df = cleaner.get_cleaned_data()
        self.assertIn(
            "Warning: Unknown cleaning method 'non_existent_method'. Skipping.",
            output[0],
        )
        assert_frame_equal(cleaned_df, original_df)

    def test_clean_data_on_non_dataframe_at_init(self):
        # If self.data was not a DataFrame (e.g., due to failed init conversion)
        cleaner_bad_data = DataCleaner(
            [1, "test", [2, 3]]
        )  # This init stores data as is
        original_bad_data = cleaner_bad_data.data  # which is the list itself

        operations = [{"method": "remove_duplicates"}]
        with Capturing() as output:
            cleaned_output = cleaner_bad_data.clean_data(operations=operations)

        self.assertTrue(
            any("Warning: Data is not a pandas DataFrame." in line for line in output)
        )
        self.assertEqual(
            cleaned_output, original_bad_data
        )  # Should return original non-DataFrame data


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
