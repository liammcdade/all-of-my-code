import unittest
from unittest.mock import patch, mock_open
import os
import json
import logging
import tempfile
import shutil
import re
from datetime import datetime

from DataNinja.core import utils  # Import the utils module


# Helper to capture print outputs (for functions that print warnings/info)
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = io.StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout


# To capture actual logging output (more robust than print for log testing)
class LogCaptureHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))


class TestLoadConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.valid_config_path = os.path.join(self.temp_dir, "valid_config.json")
        self.malformed_config_path = os.path.join(
            self.temp_dir, "malformed_config.json"
        )
        self.empty_json_path = os.path.join(
            self.temp_dir, "empty.json"
        )  # Valid empty JSON like {}
        self.empty_file_path = os.path.join(
            self.temp_dir, "empty_file.json"
        )  # Zero bytes

        self.valid_config_data = {"key": "value", "number": 123}
        with open(self.valid_config_path, "w") as f:
            json.dump(self.valid_config_data, f)

        with open(self.malformed_config_path, "w") as f:
            f.write(
                "{'key': 'value',"
            )  # Malformed JSON (single quotes, trailing comma)

        with open(self.empty_json_path, "w") as f:
            json.dump({}, f)  # Valid empty JSON object

        with open(self.empty_file_path, "w") as f:
            pass  # Zero byte file, not valid JSON

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_load_valid_config(self):
        config = utils.load_config(self.valid_config_path)
        self.assertEqual(config, self.valid_config_data)

    def test_load_non_existent_config(self):
        non_existent_path = os.path.join(self.temp_dir, "no_such_file.json")
        with Capturing() as output:  # Captures print warnings
            config = utils.load_config(non_existent_path)
        self.assertIsNone(config)
        self.assertTrue(
            any(
                f"Warning: Configuration file '{non_existent_path}' not found." in line
                for line in output
            )
        )

    def test_load_malformed_config(self):
        with Capturing() as output:
            config = utils.load_config(self.malformed_config_path)
        self.assertIsNone(config)
        self.assertTrue(
            any(
                f"Warning: Error decoding JSON from '{self.malformed_config_path}'."
                in line
                for line in output
            )
        )

    def test_load_valid_empty_json_config(self):
        config = utils.load_config(self.empty_json_path)
        self.assertEqual(config, {})  # Expecting an empty dictionary

    def test_load_empty_file_not_valid_json(self):
        # A zero-byte file is not valid JSON. Expect JSONDecodeError.
        with Capturing() as output:
            config = utils.load_config(self.empty_file_path)
        self.assertIsNone(config)
        self.assertTrue(
            any(
                f"Warning: Error decoding JSON from '{self.empty_file_path}'." in line
                for line in output
            )
        )


class TestSetupLogging(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.temp_dir, "test_app.log")
        self.module_log_path = os.path.join(self.temp_dir, "module_specific.log")
        # Ensure a clean slate for loggers we will test by name
        self.loggers_to_clear = [
            "TestLogger.Setup",
            "TestLogger.Level",
            "TestLogger.File",
            "TestLogger.NoFile",
            "DataNinjaApp",
            "MyModule.Test",
        ]
        for name in self.loggers_to_clear:
            if name in logging.Logger.manager.loggerDict:
                logger = logging.getLogger(name)
                logger.handlers = []

    def tearDown(self):
        # It's important to close file handlers before trying to remove the directory
        for name in self.loggers_to_clear:
            if name in logging.Logger.manager.loggerDict:
                logger = logging.getLogger(name)
                for handler in list(logger.handlers):  # Iterate over a copy
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                    logger.removeHandler(handler)
        shutil.rmtree(self.temp_dir)

    def test_returns_logger_instance(self):
        logger = utils.setup_logging(module_name="TestLogger.Setup")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "TestLogger.Setup")

    def test_set_log_level(self):
        logger_debug = utils.setup_logging(
            log_level=logging.DEBUG, module_name="TestLogger.Level"
        )
        self.assertEqual(logger_debug.level, logging.DEBUG)

        # Test with string level
        logger_info = utils.setup_logging(
            log_level="INFO", module_name="TestLogger.Level"
        )
        # Note: setup_logging sets logger.level, but actual handler level might differ.
        # The test here checks the logger's effective level.
        self.assertEqual(logger_info.level, logging.INFO)

    def test_log_file_creation_and_write_explicit_log_file(self):
        logger = utils.setup_logging(
            log_level=logging.INFO,
            module_name="TestLogger.File",
            log_file=self.log_file_path,
        )
        self.assertTrue(os.path.exists(self.log_file_path))

        test_message = "File logging test message - explicit path."
        logger.info(test_message)

        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()

        with open(self.log_file_path, "r") as f:
            content = f.read()
        self.assertIn(test_message, content)
        self.assertTrue(
            any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        )

    def test_log_file_for_dataninjaapp_module_default_path(self):
        # This test relies on the specific logic: if module_name is "DataNinjaApp" and log_file is None,
        # it defaults to DEFAULT_LOG_FILE ('dataninja_app.log').
        # We'll use a temporary default log file name for this test.
        default_log_filename = utils.DEFAULT_LOG_FILE
        temp_default_log_path = os.path.join(self.temp_dir, default_log_filename)

        # Temporarily patch DEFAULT_LOG_FILE for predictable path in test
        with patch("DataNinja.core.utils.DEFAULT_LOG_FILE", temp_default_log_path):
            logger = utils.setup_logging(
                module_name="DataNinjaApp", log_level=logging.INFO
            )  # log_file is None by default

        self.assertTrue(os.path.exists(temp_default_log_path))
        self.assertTrue(
            any(
                isinstance(h, logging.FileHandler)
                and h.baseFilename == temp_default_log_path
                for h in logger.handlers
            )
        )

    def test_no_log_file_if_not_specified_and_not_dataninjaapp(self):
        logger = utils.setup_logging(
            module_name="TestLogger.NoFile", log_file=None
        )  # Explicitly None
        self.assertFalse(
            any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        )
        # Check console output for "Outputting to console only"
        # This requires capturing the log output of setup_logging itself.
        log_capture_handler = LogCaptureHandler()
        logger.addHandler(
            log_capture_handler
        )  # Add to the logger returned by setup_logging

        # Re-run setup_logging to capture its internal logging
        # Note: This is a bit tricky as setup_logging itself configures the logger.
        # A better way might be to check logger.handlers directly as done above.
        # The "Outputting to console only" message is an INFO message from setup_logging.
        # To capture it, the logger used by setup_logging needs a handler.
        # Let's test this by checking the messages of the logger we just configured.
        self.assertTrue(
            any(
                "Outputting to console only." in msg
                for msg in log_capture_handler.records
            )
        )

    def test_multiple_calls_do_not_duplicate_handlers(self):
        module_name = "TestLogger.MultiCall"
        logger = utils.setup_logging(module_name=module_name, log_level=logging.INFO)
        num_handlers_first_call = len(logger.handlers)

        logger_second = utils.setup_logging(
            module_name=module_name, log_level=logging.DEBUG
        )
        num_handlers_second_call = len(logger_second.handlers)

        self.assertEqual(
            num_handlers_second_call, num_handlers_first_call
        )  # Should be same or based on re-config logic
        # Current logic clears and re-adds, so number of handlers should be consistent (e.g., 1 for console, 2 if file)
        # If only console, expect 1. If file, expect 2.
        self.assertTrue(num_handlers_second_call == 1 or num_handlers_second_call == 2)


class TestEnsureDirectoryExists(unittest.TestCase):
    def setUp(self):
        self.base_temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.base_temp_dir)

    def test_create_new_single_directory(self):
        new_dir = os.path.join(self.base_temp_dir, "new_dir")
        self.assertFalse(os.path.exists(new_dir))
        with Capturing() as output:
            result = utils.ensure_directory_exists(new_dir)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(new_dir) and os.path.isdir(new_dir))
        self.assertIn(f"Directory created: {new_dir}", output)

    def test_create_new_directory_tree(self):
        new_dir_tree = os.path.join(self.base_temp_dir, "parent", "child", "grandchild")
        self.assertFalse(os.path.exists(new_dir_tree))
        result = utils.ensure_directory_exists(new_dir_tree)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(new_dir_tree) and os.path.isdir(new_dir_tree))

    def test_existing_directory(self):
        existing_dir = os.path.join(self.base_temp_dir, "existing_dir")
        os.makedirs(existing_dir)  # Create it first
        self.assertTrue(os.path.exists(existing_dir))
        with Capturing() as output:
            result = utils.ensure_directory_exists(existing_dir)
        self.assertTrue(result)  # Should return True
        self.assertTrue(os.path.exists(existing_dir))  # Still exists
        self.assertEqual(len(output), 0)  # No "Directory created" message

    @patch("os.makedirs")
    def test_creation_oserror(self, mock_makedirs):
        mock_makedirs.side_effect = OSError("Test OS error")
        error_dir = os.path.join(self.base_temp_dir, "error_dir")
        with Capturing() as output:
            result = utils.ensure_directory_exists(error_dir)
        self.assertFalse(result)
        self.assertTrue(
            any(f"Error creating directory {error_dir}" in line for line in output)
        )


class TestGenerateTimestampedFilename(unittest.TestCase):
    @patch("DataNinja.core.utils.datetime")
    def test_filename_format_with_prefix_and_dot_extension(self, mock_datetime):
        fixed_now = datetime(2023, 10, 26, 14, 30, 55)
        mock_datetime.now.return_value = fixed_now

        filename = utils.generate_timestamped_filename("report", ".csv", prefix="daily")
        expected_filename = "daily_report_20231026_143055.csv"
        self.assertEqual(filename, expected_filename)

    @patch("DataNinja.core.utils.datetime")
    def test_filename_format_no_prefix_no_dot_extension(self, mock_datetime):
        fixed_now = datetime(2023, 1, 5, 8, 5, 10)
        mock_datetime.now.return_value = fixed_now

        filename = utils.generate_timestamped_filename("outputData", "txt")
        expected_filename = "outputData_20230105_080510.txt"
        self.assertEqual(filename, expected_filename)

    def test_filename_dynamic_timestamp(self):
        # Test without mocking to ensure it runs, format is main check
        base = "log"
        ext = "log"
        filename = utils.generate_timestamped_filename(base, ext)
        # Regex to check the format: basename_YYYYMMDD_HHMMSS.ext
        # \d{8} matches 8 digits for date, \d{6} matches 6 digits for time
        pattern = re.compile(rf"{base}_\d{8}_\d{6}\.{ext}")
        self.assertIsNotNone(pattern.match(filename))


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
# Need to import sys for Capturing helper.
import sys
