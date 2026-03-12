import unittest
import os
import yaml  # PyYAML
import tempfile
import shutil
from datetime import date  # For non-serializable test
import logging

from DataNinja.formats.yaml_handler import YAMLHandler
from DataNinja.core.loader import DataLoader  # For inheritance check


# Helper to capture log messages
class LogCaptureHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))

    def get_messages(self):
        return self.records


class TestYAMLHandlerInitialization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_yaml_path = os.path.join(self.temp_dir, "sample_init.yaml")
        with open(self.sample_yaml_path, "w") as f:
            yaml.dump({"test": "data"}, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_initialization_valid_source(self):
        handler = YAMLHandler(source=self.sample_yaml_path)
        self.assertEqual(handler.source, self.sample_yaml_path)
        self.assertIsInstance(handler.logger, logging.Logger)

    def test_get_source_info(self):
        handler = YAMLHandler(source=self.sample_yaml_path)
        self.assertEqual(
            handler.get_source_info(), f"Data source: {self.sample_yaml_path}"
        )

    def test_init_empty_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            YAMLHandler(source="")

    def test_init_none_source_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Data source cannot be empty."):
            YAMLHandler(source=None)


class TestYAMLHandlerLoadData(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dict_yaml_path = os.path.join(self.temp_dir, "dict.yaml")
        self.list_yaml_path = os.path.join(self.temp_dir, "list.yaml")
        self.nested_yaml_path = os.path.join(self.temp_dir, "nested.yaml")
        self.malformed_yaml_path = os.path.join(self.temp_dir, "malformed.yaml")
        self.empty_file_path = os.path.join(self.temp_dir, "empty.yaml")  # 0-byte
        self.empty_content_yaml_path = os.path.join(
            self.temp_dir, "empty_content.yaml"
        )  # contains 'null'
        self.utf16_yaml_path = os.path.join(self.temp_dir, "utf16.yaml")

        self.dict_data = {
            "key": "value",
            "number": 123,
            "boolean": True,
            "unicode": "éàçüö",
        }
        with open(self.dict_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(self.dict_data, f, allow_unicode=True)

        self.list_data = ["item1", "item2", {"sub_item": "sub_val_éàç"}]
        with open(self.list_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(self.list_data, f, allow_unicode=True)

        self.nested_data = {
            "config": {"version": 1.2, "params": ["a", "b_éàç"]},
            "data": [1, 2, 3],
        }
        with open(self.nested_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(self.nested_data, f, allow_unicode=True)

        with open(self.malformed_yaml_path, "w") as f:
            f.write(
                "key: value\n  bad_indent: true\n another_key: [missing_close_bracket"
            )

        open(self.empty_file_path, "w").close()  # Create 0-byte file

        with open(self.empty_content_yaml_path, "w") as f:
            f.write("null")  # Valid YAML for None

        # Create a file with different encoding
        self.utf16_data = {"message": "你好世界"}  # Hello World in Chinese
        with open(self.utf16_yaml_path, "w", encoding="utf-16") as f:
            yaml.dump(self.utf16_data, f, allow_unicode=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_load_dict_yaml(self):
        handler = YAMLHandler(source=self.dict_yaml_path)
        loaded_data = handler.load_data()  # Default encoding is utf-8 in handler
        self.assertEqual(loaded_data, self.dict_data)

    def test_load_list_yaml(self):
        handler = YAMLHandler(source=self.list_yaml_path)
        loaded_data = handler.load_data()
        self.assertEqual(loaded_data, self.list_data)

    def test_load_nested_yaml(self):
        handler = YAMLHandler(source=self.nested_yaml_path)
        loaded_data = handler.load_data()
        self.assertEqual(loaded_data, self.nested_data)

    def test_load_with_specific_encoding_kwarg(self):
        handler = YAMLHandler(source=self.utf16_yaml_path)
        loaded_data = handler.load_data(encoding="utf-16")
        self.assertEqual(loaded_data, self.utf16_data)

    def test_load_non_existent_file_raises_file_not_found(self):
        handler = YAMLHandler(source=os.path.join(self.temp_dir, "i_do_not_exist.yaml"))
        with self.assertRaises(FileNotFoundError):
            handler.load_data()

    def test_load_malformed_yaml_raises_yaml_error(self):
        handler = YAMLHandler(source=self.malformed_yaml_path)
        with self.assertRaises(
            yaml.YAMLError
        ):  # PyYAML raises YAMLError or its subclasses
            handler.load_data()

    def test_load_empty_file_returns_none(self):  # 0-byte file
        handler = YAMLHandler(source=self.empty_file_path)
        loaded_data = handler.load_data()
        self.assertIsNone(loaded_data)  # PyYAML safe_load on empty stream returns None

    def test_load_empty_content_yaml_returns_none(self):  # file contains 'null'
        handler = YAMLHandler(source=self.empty_content_yaml_path)
        loaded_data = handler.load_data()
        self.assertIsNone(loaded_data)  # YAML 'null' should parse to Python None


class TestYAMLHandlerSaveData(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_path = os.path.join(self.temp_dir, "output.yaml")
        self.output_subdir_path = os.path.join(
            self.temp_dir, "subdir_save", "output_sub.yaml"
        )
        self.handler = YAMLHandler(
            source="dummy_source_for_saving.yaml"
        )  # Source not used for saving

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_save_dictionary(self):
        data_to_save = {
            "name": "Test Config",
            "version": 1.0,
            "active": True,
            "unicode_val": "éàç",
        }
        self.handler.save_data(data_to_save, target_path=self.output_path)

        self.assertTrue(os.path.exists(self.output_path))
        reloaded_data = YAMLHandler(source=self.output_path).load_data()
        self.assertEqual(reloaded_data, data_to_save)

    def test_save_list(self):
        data_to_save = [1, "test_éàç", {"key": [True, None]}, 3.14]
        self.handler.save_data(data_to_save, target_path=self.output_path)

        self.assertTrue(os.path.exists(self.output_path))
        reloaded_data = YAMLHandler(source=self.output_path).load_data()
        self.assertEqual(reloaded_data, data_to_save)

    def test_save_nested_structure(self):
        data_to_save = {
            "level1": {
                "name": "L1",
                "children": [{"name": "L2_child1_éàç", "value": 100}],
            }
        }
        self.handler.save_data(data_to_save, target_path=self.output_path)
        reloaded_data = YAMLHandler(source=self.output_path).load_data()
        self.assertEqual(reloaded_data, data_to_save)

    def test_save_with_kwargs_indent_sort_keys_allow_unicode(self):
        data_to_save = {"z_key": 26, "a_key": 1, "c_key": 3, "unicode_char": "üöä"}
        # Save with indent, sorted keys, and ensure unicode is handled
        self.handler.save_data(
            data_to_save,
            target_path=self.output_path,
            indent=4,
            sort_keys=True,
            allow_unicode=True,
        )

        with open(self.output_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for indent (e.g., '    a_key: 1')
        self.assertIn("    a_key: 1", content)
        # Check for sorted keys (a_key should appear before c_key, c_key before z_key)
        self.assertTrue(
            content.find("a_key:") < content.find("c_key:") < content.find("z_key:")
        )
        # Check for unicode character
        self.assertIn("üöä", content)

        # Verify by reloading
        reloaded_data = YAMLHandler(source=self.output_path).load_data(encoding="utf-8")
        self.assertEqual(reloaded_data, data_to_save)

    def test_save_data_creates_subdirectory(self):
        data_to_save = {"message": "Testing subdirectory creation"}
        self.handler.save_data(data_to_save, target_path=self.output_subdir_path)
        self.assertTrue(os.path.exists(self.output_subdir_path))
        reloaded_data = YAMLHandler(source=self.output_subdir_path).load_data()
        self.assertEqual(reloaded_data, data_to_save)

    def test_save_data_no_target_path_raises_valueerror(self):
        data_to_save = {"data": [1]}
        with self.assertRaisesRegex(
            ValueError, "Target path for saving YAML data is required."
        ):
            self.handler.save_data(data_to_save, target_path=None)

    def test_save_data_non_yaml_serializable_raises_error(self):
        # PyYAML raises YAMLError (specifically RepresenterError) or TypeError for objects
        # it doesn't know how to represent. The handler catches these.
        class MyCustomObject:
            def __init__(self, value):
                self.value = value

            # No YAML representer defined for this class

        data_with_custom_obj = {"obj": MyCustomObject(10)}
        # Expect YAMLError from PyYAML, which is caught and re-raised by handler.
        # Or TypeError if PyYAML's internal error handling results in that.
        with self.assertRaises((yaml.YAMLError, TypeError)) as context:
            self.handler.save_data(data_with_custom_obj, target_path=self.output_path)
        # Check if the exception message contains relevant info about representation
        self.assertTrue(
            "represent" in str(context.exception).lower()
            or "serializable" in str(context.exception).lower()
        )


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
