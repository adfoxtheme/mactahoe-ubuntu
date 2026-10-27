import json
from pathlib import Path
import tempfile
import unittest

from model import DEFAULTS, RestTimer, clean_settings, fetch_weather, load_settings, save_settings


class SettingsTests(unittest.TestCase):
    def test_invalid_and_untrusted_types(self):
        self.assertEqual(clean_settings([]), DEFAULTS)
        settings = clean_settings({"show_clock": "false", "latitude": float("nan"),
                                   "longitude": 999, "rest_minutes": -1, "city": 12})
        self.assertTrue(settings["show_clock"])
        self.assertEqual(settings["latitude"], DEFAULTS["latitude"])
        self.assertEqual(settings["longitude"], 180)
        self.assertEqual(settings["rest_minutes"], 1)
        self.assertEqual(settings["city"], DEFAULTS["city"])

    def test_save_load_and_malformed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "widgets.json"
            self.assertEqual(load_settings(path), DEFAULTS)
            save_settings({**DEFAULTS, "city": "Đà Nẵng"}, path)
            self.assertEqual(load_settings(path)["city"], "Đà Nẵng")
            self.assertTrue(json.loads(path.read_text(encoding="utf-8")))
            path.write_text("{broken")
            self.assertEqual(load_settings(path), DEFAULTS)


class WeatherTests(unittest.TestCase):
    def test_city_and_open_meteo(self):
        urls = []
        def fetch(url):
            urls.append(url)
            if "geocoding" in url:
                return {"results": [{"latitude": 10, "longitude": 20, "name": "Huế"}]}
            return {"current": {"temperature_2m": 28, "relative_humidity_2m": 80,
                                "weather_code": 3, "wind_speed_10m": 12}}
        weather = fetch_weather(DEFAULTS, fetch)
        self.assertEqual(weather["city"], "Huế")
        self.assertEqual(weather["description"], "Có mây")
        self.assertIn("latitude=10", urls[1])

    def test_coordinates_and_openweather_units(self):
        def fetch(url):
            self.assertIn("api.openweathermap.org", url)
            return {"main": {"temp": 30, "humidity": 60}, "wind": {"speed": 2},
                    "weather": [{"description": "mưa"}]}
        weather = fetch_weather({**DEFAULTS, "city": "", "weather_api_key": "test"}, fetch)
        self.assertEqual(weather["wind"], 7.2)
        self.assertEqual(weather["source"], "OpenWeather")

    def test_unknown_city(self):
        with self.assertRaises(ValueError):
            fetch_weather(DEFAULTS, lambda _: {"results": []})


class RestTests(unittest.TestCase):
    def test_work_break_transitions_notify_once(self):
        now = [0]
        timer = RestTimer(lambda: now[0])
        self.assertEqual(timer.tick(25, 5), (1500, None))
        now[0] = 1500
        self.assertEqual(timer.tick(25, 5), (300, "break"))
        self.assertEqual(timer.tick(25, 5), (300, None))
        now[0] = 1800
        self.assertEqual(timer.tick(25, 5), (1500, "work"))
        timer.start_break()
        self.assertTrue(timer.on_break)
        timer.reset()
        self.assertFalse(timer.on_break)


if __name__ == "__main__":
    unittest.main()
