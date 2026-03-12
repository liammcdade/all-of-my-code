import unittest
import os
import pandas as pd
from pandas.testing import assert_frame_equal
import tempfile
import shutil  # For tearDown
import logging

from DataNinja.core.loader import DataLoader
from DataNinja.formats.csv_handler import CSVHandler


# Dummy concrete loader for testing DataLoader ABC aspects
class MyMockLoader(DataLoader):
    def load_data(self):
        if self.source == "test.mock":
            return "mock_data"
        elif self.source == "nonexistent.mock":
            raise FileNotFoundError("Mock file not found")
        # Call super().load_data() to hit the NotImplementedError
        # if no specific condition is met for the source.
        # To explicitly test the @abstractmethod's NotImplementedError:
        elif self.source == "trigger_not_implemented.mock":
            return super().load_data()  # This should raise NotImplementedError

        # Fallback for any other source if not explicitly handled above
        # For robustness in a mock, you might want to define behavior or raise an error
        raise ValueError(f"Unhandled source in MyMockLoader: {self.source}")


class TestDataLoaderABC(unittest.TestCase):
    def test_cannot_instantiate_dataloader(self):
        # Regex to match the error message which can vary slightly between Python versions
        # Python 3.9+ "DataLoader with abstract method load_data"
        # Older might be "DataLoader with abstract methods load_data"
        with self.assertRaisesRegex(
            TypeError,
            "Can't instantiate abstract class DataLoader with abstract method load_data",
        ):
            DataLoader(source="some_source")

    def test_mock_loader_init_valid_source(self):
        loader = MyMockLoader(source="test.mock")
        self.assertEqual(loader.source, "test.mock")
        self.assertEqual(loader.get_source_info(), "Data source: test.mock")

    def test_mock_loader_load_data_implemented_path(self):
        loader = MyMockLoader(source="test.mock")
        self.assertEqual(loader.load_data(), "mock_data")

    def test_mock_loader_load_data_raises_filenotfound(self):
        loader = MyMockLoader(source="nonexistent.mock")
        with self.assertRaisesRegex(FileNotFoundError, "Mock file not found"):
            loader.load_data()

    def test_mock_loader_load_data_abstractmethod_not_implemented(self):
        # This test ensures that if a subclass forgets to implement load_data,
        # or calls super().load_data() incorrectly, NotImplementedError is raised.
        loader = MyMockLoader(source="trigger_not_implemented.mock")
        with self.assertRaises(NotImplementedError):
            loader.load_data()

    def test_init_empty_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            MyMockLoader(source="")


class TestCSVHandler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.valid_csv_path = os.path.join(self.temp_dir, "valid.csv")
        self.empty_csv_path = os.path.join(self.temp_dir, "empty.csv")
        self.malformed_csv_path = os.path.join(self.temp_dir, "malformed.csv")
        self.output_csv_path = os.path.join(self.temp_dir, "output.csv")
        self.output_subdir_csv_path = os.path.join(
            self.temp_dir, "subdir", "output_in_subdir.csv"
        )

        self.sample_df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        self.sample_df.to_csv(self.valid_csv_path, index=False)

        with open(self.empty_csv_path, "w") as f:
            # Create empty file
            pass

        with open(self.malformed_csv_path, "w") as f:
            # Malformed: too many values in one row
            f.write("col1,col2\n1,val1,extraval\n2,val2")

        # Suppress logging output during tests for cleaner test results
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        logging.disable(logging.NOTSET)  # Re-enable logging

    def test_initialization(self):
        handler = CSVHandler(source=self.valid_csv_path)
        self.assertEqual(handler.source, self.valid_csv_path)
        self.assertEqual(
            handler.get_source_info(), f"Data source: {self.valid_csv_path}"
        )

    def test_load_valid_csv(self):
        handler = CSVHandler(source=self.valid_csv_path)
        loaded_df = handler.load_data()
        assert_frame_equal(loaded_df, self.sample_df)

    def test_load_valid_csv_with_kwargs(self):
        content_with_kwargs = "## Comment line\n## Another comment\nA;B\n1;x\n2;y"
        path_kwargs_csv = os.path.join(self.temp_dir, "kwargs.csv")
        with open(path_kwargs_csv, "w") as f:
            f.write(content_with_kwargs)

        handler = CSVHandler(source=path_kwargs_csv)
        # Using comment char '#' which is not standard for pd.read_csv,
        # but `skiprows` or `comment` can be used. Here `comment='#'`
        loaded_df = handler.load_data(sep=";", comment="#")
        expected_df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        assert_frame_equal(loaded_df, expected_df)

    def test_load_empty_csv_returns_empty_dataframe(self):
        handler = CSVHandler(source=self.empty_csv_path)
        loaded_df = handler.load_data()
        self.assertTrue(loaded_df.empty)

    def test_load_non_existent_csv_raises_file_not_found(self):
        non_existent_path = os.path.join(self.temp_dir, "i_do_not_exist.csv")
        handler = CSVHandler(source=non_existent_path)
        with self.assertRaisesRegex(
            FileNotFoundError, f"File not found: {non_existent_path}"
        ):
            handler.load_data()

    def test_load_malformed_csv_raises_parser_error(self):
        handler = CSVHandler(source=self.malformed_csv_path)
        with self.assertRaises(pd.errors.ParserError):
            handler.load_data()

    def test_save_data_creates_file_and_verifies_content(self):
        # Source for init is not strictly needed for save, but CSVHandler requires it.
        handler = CSVHandler(source="dummy_source_for_init.csv")
        df_to_save = pd.DataFrame({"col_x": [100, 200], "col_y": ["val_a", "val_b"]})
        handler.save_data(df_to_save, target_path=self.output_csv_path)

        self.assertTrue(os.path.exists(self.output_csv_path))
        reloaded_df = pd.read_csv(
            self.output_csv_path
        )  # Default index=False in save_data
        assert_frame_equal(reloaded_df, df_to_save)

    def test_save_data_with_kwargs(self):
        handler = CSVHandler(source="dummy.csv")
        df_to_save = pd.DataFrame({"val": [1.123, 2.234]})
        # Save with index and specific float format
        handler.save_data(
            df_to_save,
            target_path=self.output_csv_path,
            index=True,
            sep="\t",
            float_format="%.2f",
        )

        # Reload and check content
        # When reading back, we need to specify the separator and that the first column is the index.
        reloaded_df = pd.read_csv(self.output_csv_path, sep="\t", index_col=0)

        # Create expected DataFrame after float formatting for comparison
        expected_df = df_to_save.copy()
        # The float_format in pandas to_csv affects the string representation in the file.
        # When reloaded, pandas infers float64. Exact string check is more reliable for float_format.
        # However, for this test, we'll check if values are close.
        assert_frame_equal(
            reloaded_df, expected_df, check_dtype=True, rtol=0.01
        )  # Allow some tolerance for float

    def test_save_data_creates_subdirectory(self):
        handler = CSVHandler(source="dummy.csv")
        df_to_save = pd.DataFrame({"data": [1, 2]})
        handler.save_data(df_to_save, target_path=self.output_subdir_csv_path)
        self.assertTrue(os.path.exists(self.output_subdir_csv_path))
        reloaded_df = pd.read_csv(self.output_subdir_csv_path)
        assert_frame_equal(reloaded_df, df_to_save)

    def test_save_data_requires_target_path(self):
        handler = CSVHandler(source="dummy.csv")
        df_to_save = pd.DataFrame({"data": [1]})
        with self.assertRaisesRegex(
            ValueError, "Target path for saving data is required."
        ):
            handler.save_data(df_to_save, target_path=None)
        with self.assertRaisesRegex(
            ValueError, "Target path for saving data is required."
        ):
            handler.save_data(df_to_save)  # Also test default None

    def test_save_data_requires_dataframe(self):
        handler = CSVHandler(source="dummy.csv")
        not_a_dataframe = "this is not a dataframe, it's a string."
        with self.assertRaisesRegex(
            ValueError, "Invalid data type. Data must be a pandas DataFrame."
        ):
            handler.save_data(not_a_dataframe, target_path=self.output_csv_path)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
