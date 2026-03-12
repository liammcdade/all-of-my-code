import unittest
import os
import pandas as pd
from pandas.testing import assert_frame_equal
import tempfile
import shutil
import logging  # For capturing log messages if needed

# Assuming DataNinja is in PYTHONPATH or structured correctly for this import
from DataNinja.formats.excel_handler import ExcelHandler
from DataNinja.core.loader import DataLoader  # To test inheritance if needed


# Helper to capture log messages (more robust than print for library code)
class LogCaptureHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))

    def get_messages(self):
        return self.records


class TestExcelHandlerInitialization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_excel_path = os.path.join(self.temp_dir, "sample_init.xlsx")
        # Create a minimal valid Excel file for init testing
        pd.DataFrame().to_excel(self.sample_excel_path, engine="openpyxl")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_initialization_valid_source(self):
        handler = ExcelHandler(source=self.sample_excel_path)
        self.assertEqual(handler.source, self.sample_excel_path)
        self.assertIsInstance(
            handler.logger, logging.Logger
        )  # Check logger is initialized

    def test_get_source_info(self):
        handler = ExcelHandler(source=self.sample_excel_path)
        self.assertEqual(
            handler.get_source_info(), f"Data source: {self.sample_excel_path}"
        )

    def test_init_empty_source_raises_valueerror(self):
        # This error is raised by the parent DataLoader class
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            ExcelHandler(source="")

    def test_init_none_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            ExcelHandler(source=None)  # DataLoader's __init__ handles this


class TestExcelHandlerLoadData(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_excel_path = os.path.join(self.temp_dir, "sample.xlsx")
        self.empty_excel_path = os.path.join(self.temp_dir, "empty.xlsx")
        self.malformed_excel_path = os.path.join(
            self.temp_dir, "malformed.xlsx"
        )  # Text file

        self.df_alpha = pd.DataFrame({"A": [1, 2], "B": ["apple", "orange"]})
        self.df_beta = pd.DataFrame({"X": [10.1, 20.2], "Y": [True, False]})

        try:
            with pd.ExcelWriter(self.sample_excel_path, engine="openpyxl") as writer:
                self.df_alpha.to_excel(writer, sheet_name="SheetAlpha", index=False)
                self.df_beta.to_excel(writer, sheet_name="SheetBeta", index=False)
        except ImportError:
            self.fail("openpyxl is required. Please ensure it's installed.")

        # Create an Excel file with one empty sheet for testing empty load
        with pd.ExcelWriter(self.empty_excel_path, engine="openpyxl") as writer:
            pd.DataFrame().to_excel(writer, sheet_name="EmptySheet", index=False)

        # Create a non-Excel file with .xlsx extension
        with open(self.malformed_excel_path, "w") as f:
            f.write("This is just a text file, not a valid Excel file.")

        # Capture log messages
        self.log_capture_handler = LogCaptureHandler()
        # Configure a logger for the ExcelHandler to capture its messages
        # ExcelHandler uses logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # The __name__ for formats.excel_handler will be DataNinja.formats.excel_handler
        self.excel_handler_logger = logging.getLogger(
            "DataNinja.formats.excel_handler.ExcelHandler"
        )
        self.excel_handler_logger.addHandler(self.log_capture_handler)
        self.excel_handler_logger.setLevel(
            logging.DEBUG
        )  # Ensure we capture all levels

    def tearDown(self):
        self.excel_handler_logger.removeHandler(self.log_capture_handler)
        shutil.rmtree(self.temp_dir)

    def test_load_specific_sheet_by_name(self):
        handler = ExcelHandler(source=self.sample_excel_path)
        loaded_df = handler.load_data(sheet_name="SheetAlpha")
        assert_frame_equal(loaded_df, self.df_alpha)

    def test_load_specific_sheet_by_index_default_is_0(self):
        handler = ExcelHandler(source=self.sample_excel_path)
        loaded_df_default = handler.load_data()  # sheet_name=0 is default
        assert_frame_equal(loaded_df_default, self.df_alpha)

        loaded_df_index_1 = handler.load_data(sheet_name=1)  # SheetBeta
        assert_frame_equal(loaded_df_index_1, self.df_beta)

    def test_load_all_sheets(self):
        handler = ExcelHandler(source=self.sample_excel_path)
        loaded_dict = handler.load_data(sheet_name=None)
        self.assertIsInstance(loaded_dict, dict)
        self.assertIn("SheetAlpha", loaded_dict)
        self.assertIn("SheetBeta", loaded_dict)
        assert_frame_equal(loaded_dict["SheetAlpha"], self.df_alpha)
        assert_frame_equal(loaded_dict["SheetBeta"], self.df_beta)

    def test_load_with_kwargs_skiprows_usecols(self):
        # Create a file with specific structure for this test
        path_kwargs_excel = os.path.join(self.temp_dir, "kwargs_test.xlsx")
        df_to_write = pd.DataFrame(
            {
                "Col0": ["skip", "skip", 1, 2, 3],
                "Col1": ["skip", "skip", "A", "B", "C"],
                "Col2": ["skip", "skip", 10.1, 20.2, 30.3],
                "Col3": ["skip", "skip", "X", "Y", "Z"],
            }
        )
        df_to_write.to_excel(
            path_kwargs_excel, sheet_name="TestSheet", index=False, header=False
        )  # No header written by pandas

        handler = ExcelHandler(source=path_kwargs_excel)
        # Skip first 2 rows, use columns 1 and 3 (0-indexed) which become headers for pandas
        # then data starts from next row.
        # So, effectively, read data from row 3 (index 2), use cols B and D (indices 1, 3).
        # After skipping 2 rows, row 3 becomes header.
        loaded_df = handler.load_data(
            sheet_name="TestSheet", skiprows=2, usecols=[1, 3], header=0
        )
        expected_df = pd.DataFrame({"Col1": ["A", "B", "C"], "Col3": ["X", "Y", "Z"]})
        assert_frame_equal(loaded_df, expected_df)

    def test_load_non_existent_file_raises_file_not_found(self):
        handler = ExcelHandler(source=os.path.join(self.temp_dir, "no_file.xlsx"))
        with self.assertRaises(FileNotFoundError):
            handler.load_data()

    def test_load_non_existent_sheet_name_raises_valueerror(self):
        handler = ExcelHandler(source=self.sample_excel_path)
        # pandas.read_excel (via openpyxl) raises ValueError if sheet name not found.
        with self.assertRaises(ValueError):
            handler.load_data(sheet_name="NoSheetHere")

    def test_load_malformed_excel_file_raises_error(self):
        handler = ExcelHandler(source=self.malformed_excel_path)
        # The error for a text file renamed to .xlsx is often zipfile.BadZipFile
        # or a similar error from openpyxl when it tries to read it as an Excel file.
        # The ExcelHandler catches this in its generic Exception block.
        with self.assertRaises(Exception) as context:
            handler.load_data()
        # Check that it's not FileNotFoundError or ValueError for sheet name
        self.assertNotIsInstance(context.exception, FileNotFoundError)
        self.assertNotIsInstance(context.exception, ValueError)
        # Could check for specific openpyxl error type if consistent, e.g.
        # from openpyxl.utils.exceptions import InvalidFileException
        # self.assertIsInstance(context.exception, InvalidFileException)
        # Or more generally, check log for "An unexpected error occurred"
        self.assertTrue(
            any(
                "An unexpected error occurred" in msg
                for msg in self.log_capture_handler.get_messages()
            )
        )

    def test_load_empty_sheet_returns_empty_dataframe(self):
        handler = ExcelHandler(source=self.empty_excel_path)
        loaded_df = handler.load_data(sheet_name="EmptySheet")
        self.assertTrue(loaded_df.empty)


class TestExcelHandlerSaveData(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_excel_path = os.path.join(self.temp_dir, "output.xlsx")
        self.output_subdir_excel_path = os.path.join(
            self.temp_dir, "subdir_test", "output_in_subdir.xlsx"
        )
        self.df_single = pd.DataFrame(
            {"Product": ["Apples", "Bananas"], "Qty": [100, 150]}
        )
        self.dict_dfs = {
            "Sales": pd.DataFrame({"Rep": ["Joe", "Liz"], "Total": [5000, 6500]}),
            "Costs": pd.DataFrame(
                {"Category": ["Office", "Travel"], "Amount": [500, 1200]}
            ),
        }
        # Dummy handler for saving, source doesn't matter if target_path is given
        self.handler = ExcelHandler(source="dummy_source.xlsx")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_save_single_dataframe(self):
        self.handler.save_data(
            self.df_single, target_path=self.output_excel_path, sheet_name="Inventory"
        )
        self.assertTrue(os.path.exists(self.output_excel_path))
        reloaded_df = pd.read_excel(
            self.output_excel_path, sheet_name="Inventory", engine="openpyxl"
        )
        assert_frame_equal(reloaded_df, self.df_single)

    def test_save_dict_of_dataframes(self):
        self.handler.save_data(
            self.dict_dfs, target_path=self.output_excel_path
        )  # Overwrites if exists
        self.assertTrue(os.path.exists(self.output_excel_path))
        reloaded_data = pd.read_excel(
            self.output_excel_path, sheet_name=None, engine="openpyxl"
        )
        self.assertIn("Sales", reloaded_data)
        self.assertIn("Costs", reloaded_data)
        assert_frame_equal(reloaded_data["Sales"], self.dict_dfs["Sales"])
        assert_frame_equal(reloaded_data["Costs"], self.dict_dfs["Costs"])

    def test_save_data_with_kwargs_index_and_startrow(self):
        # Save with index=True and startrow=2
        self.handler.save_data(
            self.df_single,
            target_path=self.output_excel_path,
            sheet_name="WithKwargs",
            index=True,
            startrow=2,
        )
        # Reload and check
        # When reading, we need to account for the startrow and the index.
        # The header will be on row 3 (index 2), data on row 4.
        # The index written will be the first column.
        reloaded_df = pd.read_excel(
            self.output_excel_path,
            sheet_name="WithKwargs",
            engine="openpyxl",
            header=2,
            index_col=0,
        )
        assert_frame_equal(reloaded_df, self.df_single)

    def test_save_data_creates_subdirectory(self):
        self.handler.save_data(
            self.df_single,
            target_path=self.output_subdir_excel_path,
            sheet_name="SubdirTest",
        )
        self.assertTrue(os.path.exists(self.output_subdir_excel_path))
        reloaded_df = pd.read_excel(self.output_subdir_excel_path, engine="openpyxl")
        assert_frame_equal(reloaded_df, self.df_single)

    def test_save_data_no_target_path_raises_valueerror(self):
        with self.assertRaisesRegex(
            ValueError, "Target path for saving Excel data is required."
        ):
            self.handler.save_data(self.df_single, target_path=None)
        with self.assertRaisesRegex(
            ValueError, "Target path for saving Excel data is required."
        ):
            self.handler.save_data(self.df_single)  # Default target_path is None

    def test_save_data_invalid_data_type_raises_typeerror(self):
        not_a_df_or_dict = "this is a string"
        with self.assertRaisesRegex(
            TypeError, "Data must be a pandas DataFrame or a dictionary of DataFrames."
        ):
            self.handler.save_data(not_a_df_or_dict, target_path=self.output_excel_path)

    def test_save_data_dict_with_invalid_value_type_raises_typeerror(self):
        dict_with_invalid_value = {
            "Sheet1": self.df_single,
            "Sheet2": "not a DataFrame",
        }
        with self.assertRaisesRegex(
            TypeError, "If data is a dict, all its values must be pandas DataFrames."
        ):
            self.handler.save_data(
                dict_with_invalid_value, target_path=self.output_excel_path
            )


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
