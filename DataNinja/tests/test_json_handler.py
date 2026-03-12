import unittest
import os
import json
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
import tempfile
import shutil
from datetime import date, datetime  # For non-serializable test
import logging

from DataNinja.formats.json_handler import JSONHandler
from DataNinja.core.loader import DataLoader  # For inheritance check if needed


# Helper to capture log messages
class LogCaptureHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))

    def get_messages(self):
        return self.records


class TestJSONHandlerInitialization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_json_path = os.path.join(self.temp_dir, "sample_init.json")
        with open(self.sample_json_path, "w") as f:
            json.dump({"test": "data"}, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_initialization_valid_source(self):
        handler = JSONHandler(source=self.sample_json_path)
        self.assertEqual(handler.source, self.sample_json_path)
        self.assertIsInstance(handler.logger, logging.Logger)

    def test_get_source_info(self):
        handler = JSONHandler(source=self.sample_json_path)
        self.assertEqual(
            handler.get_source_info(), f"Data source: {self.sample_json_path}"
        )

    def test_init_empty_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            JSONHandler(source="")

    def test_init_none_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            JSONHandler(source=None)


class TestJSONHandlerLoadData(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.records_path = os.path.join(self.temp_dir, "records.json")
        self.nested_obj_path = os.path.join(self.temp_dir, "nested_object.json")
        self.lines_path = os.path.join(self.temp_dir, "lines.jsonl")
        self.empty_array_path = os.path.join(self.temp_dir, "empty_array.json")
        self.empty_object_path = os.path.join(self.temp_dir, "empty_object.json")
        self.malformed_path = os.path.join(self.temp_dir, "malformed.json")

        self.df_records_data = [{"id": 1, "val": "A"}, {"id": 2, "val": "B"}]
        with open(self.records_path, "w") as f:
            json.dump(self.df_records_data, f)

        self.nested_dict_data = {"key": "value", "list_items": [1, {"sub": "val"}]}
        with open(self.nested_obj_path, "w") as f:
            json.dump(self.nested_dict_data, f)

        with open(self.lines_path, "w") as f:
            f.write('{"id": 10, "item": "X"}\n')
            f.write('{"id": 20, "item": "Y"}\n')

        with open(self.empty_array_path, "w") as f:
            json.dump([], f)

        with open(self.empty_object_path, "w") as f:
            json.dump({}, f)

        with open(self.malformed_path, "w") as f:
            f.write('{"key": "value", missing_comma "another": "val"}')

        self.log_capture_handler = LogCaptureHandler()
        self.json_handler_logger = logging.getLogger(
            "DataNinja.formats.json_handler.JSONHandler"
        )
        self.json_handler_logger.addHandler(self.log_capture_handler)
        self.json_handler_logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.json_handler_logger.removeHandler(self.log_capture_handler)
        shutil.rmtree(self.temp_dir)

    def test_load_records_json_to_dataframe(self):
        handler = JSONHandler(source=self.records_path)
        # The handler's load_data first tries pd.read_json.
        # If orient is not specified, pandas attempts to infer.
        # For a list of dicts, 'records' is often inferred or a good default.
        loaded_df = handler.load_data(orient="records")
        expected_df = pd.DataFrame(self.df_records_data)
        assert_frame_equal(loaded_df, expected_df)

    def test_load_json_lines_to_dataframe(self):
        handler = JSONHandler(source=self.lines_path)
        loaded_df = handler.load_data(
            lines=True, orient="records"
        )  # lines=True is key for .jsonl
        expected_df = pd.DataFrame([{"id": 10, "item": "X"}, {"id": 20, "item": "Y"}])
        assert_frame_equal(loaded_df, expected_df)

    def test_load_nested_json_falls_back_to_json_load(self):
        handler = JSONHandler(source=self.nested_obj_path)
        # pd.read_json would typically raise ValueError for a single complex dict
        # not conforming to a tabular structure, triggering the fallback.
        loaded_data = handler.load_data()
        self.assertEqual(loaded_data, self.nested_dict_data)
        self.assertIsInstance(loaded_data, dict)
        self.assertTrue(
            any(
                "Pandas failed to parse JSON" in msg
                for msg in self.log_capture_handler.get_messages()
            )
        )

    def test_load_non_existent_file_raises_file_not_found(self):
        handler = JSONHandler(source=os.path.join(self.temp_dir, "no_file_here.json"))
        with self.assertRaises(FileNotFoundError):
            handler.load_data()

    def test_load_malformed_json_raises_json_decode_error(self):
        handler = JSONHandler(source=self.malformed_path)
        # Expecting JSONDecodeError from the json.load fallback.
        with self.assertRaises(json.JSONDecodeError):
            handler.load_data()
        self.assertTrue(
            any(
                "JSONDecodeError parsing" in msg
                for msg in self.log_capture_handler.get_messages()
            )
        )

    def test_load_empty_array_json(self):
        handler = JSONHandler(source=self.empty_array_path)
        # pd.read_json on an empty array '[]' usually produces an empty DataFrame.
        loaded_data = handler.load_data()
        self.assertIsInstance(loaded_data, pd.DataFrame)
        self.assertTrue(loaded_data.empty)

    def test_load_empty_object_json(self):
        handler = JSONHandler(source=self.empty_object_path)
        # pd.read_json on an empty object '{}' typically raises ValueError.
        # This should trigger the fallback to json.load.
        loaded_data = handler.load_data()
        self.assertEqual(loaded_data, {})
        self.assertIsInstance(loaded_data, dict)
        self.assertTrue(
            any(
                "Pandas failed to parse JSON" in msg
                for msg in self.log_capture_handler.get_messages()
            )
        )


class TestJSONHandlerSaveData(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_path = os.path.join(self.temp_dir, "output.json")
        self.output_subdir_path = os.path.join(
            self.temp_dir, "subdir_save", "output_sub.json"
        )
        self.handler = JSONHandler(
            source="dummy_source_for_saving.json"
        )  # Source not used for saving

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_save_dataframe_default_is_json_lines(self):
        df_to_save = pd.DataFrame([{"X": 1, "Y": "alpha"}, {"X": 2, "Y": "beta"}])
        # Handler default for DataFrame: orient='records', lines=True, indent=None
        self.handler.save_data(df_to_save, target_path=self.output_path)

        self.assertTrue(os.path.exists(self.output_path))
        results = []
        with open(self.output_path, "r") as f:
            for line in f:
                results.append(json.loads(line))
        expected_data = df_to_save.to_dict(orient="records")
        self.assertEqual(results, expected_data)

    def test_save_dataframe_orient_table_with_indent(self):
        df_to_save = pd.DataFrame([{"ColA": 10, "ColB": "zeta"}])
        # Override defaults: orient='table', lines=False (implied by not 'records'), indent=4
        self.handler.save_data(
            df_to_save, target_path=self.output_path, orient="table", indent=4
        )

        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r") as f:
            reloaded_data_dict = json.load(f)  # Should be a single JSON object

        # Convert dict back to DataFrame using pandas read_json for comparison
        # Note: pd.read_json(orient='table') expects a specific schema.
        # The to_json(orient='table') produces this.
        reloaded_df = pd.read_json(json.dumps(reloaded_data_dict), orient="table")
        assert_frame_equal(reloaded_df, df_to_save, check_dtype=False)

    def test_save_python_dictionary(self):
        dict_to_save = {"project_name": "DataNinja", "status": "active", "version": 2.1}
        self.handler.save_data(
            dict_to_save, target_path=self.output_path, indent=2, sort_keys=True
        )

        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r") as f:
            reloaded_data = json.load(f)
        self.assertEqual(reloaded_data, dict_to_save)
        # Check if sorted (first key should be 'project_name' if sort_keys=True)
        # This depends on Python version for dict ordering if not sorted, but json.dump sort_keys is reliable.
        with open(self.output_path, "r") as f:
            raw_content = f.read()
        self.assertTrue(
            raw_content.find('"project_name"') < raw_content.find('"status"')
        )

    def test_save_python_list(self):
        list_to_save = [{"item_id": "A1"}, {"item_id": "B2", "props": [1, 2, 3]}]
        self.handler.save_data(
            list_to_save, target_path=self.output_path, indent=None
        )  # No pretty print

        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r") as f:
            reloaded_data = json.load(f)
        self.assertEqual(reloaded_data, list_to_save)

    def test_save_data_creates_subdirectory(self):
        df_to_save = pd.DataFrame({"test_col": [True]})
        self.handler.save_data(df_to_save, target_path=self.output_subdir_path)
        self.assertTrue(os.path.exists(self.output_subdir_path))

    def test_save_data_no_target_path_raises_valueerror(self):
        df_to_save = pd.DataFrame({"data_col": [1]})
        with self.assertRaisesRegex(
            ValueError, "Target path for saving JSON data is required."
        ):
            self.handler.save_data(df_to_save, target_path=None)

    def test_save_data_unsupported_type_raises_typeerror(self):
        # Example of a type not handled: set
        unsupported_data = {"a", "b", "c"}
        with self.assertRaisesRegex(
            TypeError, "Unsupported data type for saving to JSON"
        ):
            self.handler.save_data(unsupported_data, target_path=self.output_path)

    def test_save_data_non_json_serializable_content_in_dict_raises_typeerror(self):
        # Test the json.dump path for dict/list containing non-serializable items
        data_with_datetime_object = {"event_time": datetime(2023, 1, 1, 10, 0, 0)}
        # json.dump cannot serialize datetime objects by default
        with self.assertRaises(
            TypeError
        ) as context:  # json.dump raises TypeError for non-serializable
            self.handler.save_data(
                data_with_datetime_object, target_path=self.output_path
            )
        self.assertIn("is not JSON serializable", str(context.exception).lower())


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
