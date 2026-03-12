import unittest
import math
import logging  # For capturing log messages

# Assuming DataNinja is in PYTHONPATH or structured correctly for this import
from DataNinja.plugins.geo import GeoProcessor
import pandas as pd  # For testing initialization with data


# Helper to capture log messages
class LogCaptureHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))

    def get_messages(self):
        return self.records


class TestGeoProcessorInitialization(unittest.TestCase):
    def test_initialization_no_data(self):
        geo_proc = GeoProcessor()
        self.assertIsNotNone(geo_proc)
        self.assertIsNone(geo_proc.data)  # data should be None if not provided
        self.assertIsInstance(geo_proc.logger, logging.Logger)

    def test_initialization_with_data(self):
        sample_df = pd.DataFrame({"col1": [1, 2]})
        geo_proc_with_data = GeoProcessor(data=sample_df)
        self.assertIsNotNone(geo_proc_with_data)
        pd.testing.assert_frame_equal(geo_proc_with_data.data, sample_df)


class TestCalculateDistance(unittest.TestCase):
    def setUp(self):
        self.geo_proc = GeoProcessor()
        # Coordinates for San Francisco (SF) and Los Angeles (LA)
        self.lat_sf, self.lon_sf = 37.7749, -122.4194
        self.lat_la, self.lon_la = 34.0522, -118.2437
        # Expected distances (approximate, for testing Haversine)
        # Calculated using an online Haversine calculator for R=6371km and R=3959miles
        self.dist_sf_la_km = 559.0  # Roughly
        self.dist_sf_la_miles = 347.3  # Roughly

        # Coordinates for London and Paris
        self.lat_london, self.lon_london = 51.5074, -0.1278
        self.lat_paris, self.lon_paris = 48.8566, 2.3522
        self.dist_london_paris_km = 343.5
        self.dist_london_paris_miles = 213.4

        # For checking floats, define a tolerance (e.g., +/- 1 km/mile)
        self.tolerance_km = 1.0
        self.tolerance_miles = 1.0

    def test_calculate_distance_sf_la_km(self):
        distance = self.geo_proc.calculate_distance(
            self.lat_sf, self.lon_sf, self.lat_la, self.lon_la, unit="km"
        )
        self.assertAlmostEqual(distance, self.dist_sf_la_km, delta=self.tolerance_km)

    def test_calculate_distance_sf_la_miles(self):
        distance = self.geo_proc.calculate_distance(
            self.lat_sf, self.lon_sf, self.lat_la, self.lon_la, unit="miles"
        )
        self.assertAlmostEqual(
            distance, self.dist_sf_la_miles, delta=self.tolerance_miles
        )

    def test_calculate_distance_london_paris_km(self):
        distance = self.geo_proc.calculate_distance(
            self.lat_london, self.lon_london, self.lat_paris, self.lon_paris, unit="km"
        )
        self.assertAlmostEqual(
            distance, self.dist_london_paris_km, delta=self.tolerance_km
        )

    def test_calculate_distance_london_paris_miles(self):
        distance = self.geo_proc.calculate_distance(
            self.lat_london,
            self.lon_london,
            self.lat_paris,
            self.lon_paris,
            unit="miles",
        )
        self.assertAlmostEqual(
            distance, self.dist_london_paris_miles, delta=self.tolerance_miles
        )

    def test_calculate_distance_zero_distance(self):
        # Distance from a point to itself should be 0
        distance_km = self.geo_proc.calculate_distance(
            self.lat_sf, self.lon_sf, self.lat_sf, self.lon_sf, unit="km"
        )
        self.assertEqual(distance_km, 0.0)
        distance_miles = self.geo_proc.calculate_distance(
            self.lat_sf, self.lon_sf, self.lat_sf, self.lon_sf, unit="miles"
        )
        self.assertEqual(distance_miles, 0.0)

    def test_calculate_distance_crossing_equator_and_prime_meridian(self):
        # Point A: North-East (e.g., 10N, 10E)
        # Point B: South-West (e.g., -10S, -10W)
        lat1, lon1 = 10.0, 10.0
        lat2, lon2 = -10.0, -10.0
        # Expected values (approx, from online calculator): ~3131 km or ~1946 miles
        expected_km = 3131.0
        expected_miles = 1945.5

        distance_km = self.geo_proc.calculate_distance(
            lat1, lon1, lat2, lon2, unit="km"
        )
        self.assertAlmostEqual(
            distance_km, expected_km, delta=self.tolerance_km * 2
        )  # Wider tolerance for longer distances

        distance_miles = self.geo_proc.calculate_distance(
            lat1, lon1, lat2, lon2, unit="miles"
        )
        self.assertAlmostEqual(
            distance_miles, expected_miles, delta=self.tolerance_miles * 2
        )

    def test_calculate_distance_invalid_coordinate_type_raises_typeerror(self):
        with self.assertRaisesRegex(TypeError, "Coordinate lat1 must be a number"):
            self.geo_proc.calculate_distance(
                "not_a_float", self.lon_sf, self.lat_la, self.lon_la
            )
        with self.assertRaisesRegex(TypeError, "Coordinate lon1 must be a number"):
            self.geo_proc.calculate_distance(
                self.lat_sf, "not_a_float", self.lat_la, self.lon_la
            )
        with self.assertRaisesRegex(TypeError, "Coordinate lat2 must be a number"):
            self.geo_proc.calculate_distance(
                self.lat_sf, self.lon_sf, "not_a_float", self.lon_la
            )
        with self.assertRaisesRegex(TypeError, "Coordinate lon2 must be a number"):
            self.geo_proc.calculate_distance(
                self.lat_sf, self.lon_sf, self.lat_la, "not_a_float"
            )

    def test_calculate_distance_invalid_unit_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Unit must be 'km' or 'miles'."):
            self.geo_proc.calculate_distance(
                self.lat_sf, self.lon_sf, self.lat_la, self.lon_la, unit="furlongs"
            )
        with self.assertRaisesRegex(ValueError, "Unit must be 'km' or 'miles'."):
            self.geo_proc.calculate_distance(
                self.lat_sf, self.lon_sf, self.lat_la, self.lon_la, unit=""
            )  # Empty unit


class TestGeocodeAddress(unittest.TestCase):
    def setUp(self):
        self.geo_proc = GeoProcessor()
        self.expected_mocked_response = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address_found": "123 Main St, Anytown, USA",
            "confidence": "mocked_high",
        }

        # Setup log capture for this test class
        self.log_capture_handler = LogCaptureHandler()
        # The logger name is 'DataNinja.plugins.geo.GeoProcessor'
        self.geo_processor_logger = logging.getLogger(
            "DataNinja.plugins.geo.GeoProcessor"
        )
        self.original_level = self.geo_processor_logger.level
        self.geo_processor_logger.addHandler(self.log_capture_handler)
        self.geo_processor_logger.setLevel(
            logging.INFO
        )  # Ensure INFO messages are captured

    def tearDown(self):
        self.geo_processor_logger.removeHandler(self.log_capture_handler)
        self.geo_processor_logger.setLevel(self.original_level)

    def test_geocode_address_returns_mocked_data(self):
        address = "1 Infinite Loop, Cupertino, CA"
        response = self.geo_proc.geocode_address(address)
        self.assertEqual(response, self.expected_mocked_response)

        # Check for warning about mocked data
        log_messages = self.log_capture_handler.get_messages()
        self.assertTrue(
            any(
                f"Geocoding is mocked for '{address}'. Returning fixed dummy data"
                in msg
                for msg in log_messages
            )
        )

    def test_geocode_address_with_api_key_logs_key_and_returns_mocked_data(self):
        address = "Eiffel Tower, Paris"
        api_key = "test_api_key_12345"
        response = self.geo_proc.geocode_address(address, api_key=api_key)
        self.assertEqual(response, self.expected_mocked_response)

        # Check for API key logging and mocked data warning
        log_messages = self.log_capture_handler.get_messages()
        self.assertTrue(
            any(
                f"Received API key: {'*' * (len(api_key) - 3) + api_key[-3:]}" in msg
                for msg in log_messages
            )
        )
        self.assertTrue(
            any(
                f"Geocoding is mocked for '{address}'. Returning fixed dummy data"
                in msg
                for msg in log_messages
            )
        )

    def test_geocode_address_invalid_address_type_raises_typeerror(self):
        with self.assertRaisesRegex(TypeError, "Address must be a string."):
            self.geo_proc.geocode_address(12345)

    def test_geocode_address_empty_address_raises_valueerror(self):
        with self.assertRaisesRegex(
            ValueError, "Address cannot be an empty or whitespace-only string."
        ):
            self.geo_proc.geocode_address("")
        with self.assertRaisesRegex(
            ValueError, "Address cannot be an empty or whitespace-only string."
        ):
            self.geo_proc.geocode_address("   ")  # Whitespace only


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
