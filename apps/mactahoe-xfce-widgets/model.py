"""Desktop-independent settings, weather and resource sampling for Tahoe widgets."""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULTS = {
    "show_clock": True, "show_weather": True, "show_system": True,
    "show_lunar": True, "show_rest": True,
    "city": "Hà Nội", "latitude": 21.0285, "longitude": 105.8542,
    "weather_api_key": "", "weather_interval": 15,
    "monitor": 0, "clock_x": 64, "clock_y": 64, "stack_x": 24, "stack_y": 64,
    "rest_minutes": 25, "break_minutes": 5,
}


def settings_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mactahoe-xfce/widgets.json"


def clean_settings(raw):
    result = DEFAULTS.copy()
    if not isinstance(raw, dict):
        return result
    for key, default in DEFAULTS.items():
        value = raw.get(key, default)
        if isinstance(default, bool):
            result[key] = value if isinstance(value, bool) else default
        elif isinstance(default, str):
            result[key] = value[:256] if isinstance(value, str) else default
        elif isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
            low, high = {
                "latitude": (-90, 90), "longitude": (-180, 180),
                "weather_interval": (5, 120), "rest_minutes": (1, 180),
                "break_minutes": (1, 60), "monitor": (0, 32),
            }.get(key, (0, 4096))
            result[key] = type(default)(max(low, min(high, value)))
    return result


def load_settings(path=None):
    try:
        return clean_settings(json.loads((path or settings_path()).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return DEFAULTS.copy()


def save_settings(settings, path=None):
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    # The optional API key belongs to this user, not other local accounts.
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(clean_settings(settings), stream, ensure_ascii=False, indent=2)
    temporary.chmod(0o600)
    temporary.replace(path)


def get_json(url):
    request = Request(url, headers={"User-Agent": "MacTahoe-Xfce/1.0"})
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def weather_label(code):
    if code == 0:
        return "Trời quang"
    if code in (1, 2, 3):
        return "Có mây"
    if code in (45, 48):
        return "Sương mù"
    if code in (71, 73, 75, 77, 85, 86):
        return "Tuyết"
    if code in (95, 96, 99):
        return "Dông"
    return "Mưa"


def fetch_weather(settings, fetch=get_json):
    lat, lon = settings["latitude"], settings["longitude"]
    city = settings["city"].strip()
    if city:
        geo = fetch("https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
            "name": city, "count": 1, "language": "vi", "format": "json",
        }))
        matches = geo.get("results", [])
        if not matches:
            raise ValueError("Không tìm thấy thành phố; để trống tên để dùng tọa độ.")
        lat, lon = matches[0]["latitude"], matches[0]["longitude"]
        city = matches[0]["name"]
    else:
        city = f"{lat:.2f}°, {lon:.2f}°"
    if settings["weather_api_key"].strip():
        data = fetch("https://api.openweathermap.org/data/2.5/weather?" + urlencode({
            "lat": lat, "lon": lon, "appid": settings["weather_api_key"].strip(),
            "units": "metric", "lang": "vi",
        }))
        return {"city": city, "temp": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"], "wind": data["wind"]["speed"] * 3.6,
                "high": data["main"].get("temp_max"), "low": data["main"].get("temp_min"),
                "condition": ('clear' if data['weather'][0]['id'] == 800 else
                              'cloud' if data['weather'][0]['id'] > 800 else
                              'storm' if data['weather'][0]['id'] < 300 else
                              'snow' if 600 <= data['weather'][0]['id'] < 700 else 'rain'),
                "night": data['weather'][0].get('icon', '').endswith('n'),
                "source": "OpenWeather"}
    data = fetch("https://api.open-meteo.com/v1/forecast?" + urlencode({
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
        "daily": "temperature_2m_max,temperature_2m_min", "timezone": "auto", "forecast_days": 1,
    }))
    daily, data = data.get("daily", {}), data["current"]
    return {"city": city, "temp": data["temperature_2m"],
            "description": weather_label(data["weather_code"]),
            "humidity": data["relative_humidity_2m"], "wind": data["wind_speed_10m"],
            "high": (daily.get("temperature_2m_max") or [None])[0],
            "low": (daily.get("temperature_2m_min") or [None])[0],
            "condition": ('clear' if data['weather_code'] == 0 else
                          'cloud' if data['weather_code'] in (1, 2, 3, 45, 48) else
                          'snow' if data['weather_code'] in (71, 73, 75, 77, 85, 86) else
                          'storm' if data['weather_code'] >= 95 else 'rain'),
            "night": not bool(data.get('is_day', 1)),
            "source": "Open-Meteo"}


def gpu_usage():
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]*/device")):
        try:
            # AMD exposes utilization here; integrated GPUs without telemetry stay hidden.
            return f"GPU  {int((card / 'gpu_busy_percent').read_text())}%"
        except (OSError, ValueError):
            pass
    if shutil.which("nvidia-smi"):
        try:
            text = subprocess.check_output([
                "nvidia-smi", "--query-gpu=name,utilization.gpu", "--format=csv,noheader,nounits",
            ], text=True, timeout=2, stderr=subprocess.DEVNULL)
            name, percent = text.splitlines()[0].rsplit(",", 1)
            return f"{name.strip()}  {percent.strip()}%"
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            pass
    return ""


class Metrics:
    def __init__(self):
        import psutil
        self.psutil = psutil
        self.previous = psutil.net_io_counters()
        self.previous_time = time.monotonic()
        self.cpu_name = "CPU"
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    self.cpu_name = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
        self.psutil.cpu_percent()

    def sample(self):
        memory = self.psutil.virtual_memory()
        disk = self.psutil.disk_usage(str(Path.home()))
        net, now = self.psutil.net_io_counters(), time.monotonic()
        seconds = max(0.01, now - self.previous_time)
        down = max(0, net.bytes_recv - self.previous.bytes_recv) / seconds / 1024
        up = max(0, net.bytes_sent - self.previous.bytes_sent) / seconds / 1024
        self.previous, self.previous_time = net, now
        gpu = gpu_usage()
        gpu_match = re.search(r'(\d+(?:\.\d+)?)%', gpu)
        return {
            "uptime": max(0, time.time()-self.psutil.boot_time()),
            "gpu_percent": float(gpu_match.group(1)) if gpu_match else None,
            "cpu_name": self.cpu_name, "cpu": self.psutil.cpu_percent(),
            "ram": memory.percent, "ram_used": memory.used / 2**30,
            "ram_total": memory.total / 2**30, "disk": disk.percent,
            "disk_free": disk.free / 2**30, "down": down, "up": up, "gpu": gpu,
        }


class RestTimer:
    def __init__(self, now=time.monotonic):
        self.now = now
        self.started = now()
        self.on_break = False

    def reset(self):
        self.started = self.now()
        self.on_break = False

    def start_break(self):
        self.started = self.now()
        self.on_break = True

    def tick(self, work_minutes, break_minutes):
        duration = (break_minutes if self.on_break else work_minutes) * 60
        remaining = max(0, math.ceil(duration - (self.now() - self.started)))
        event = None
        if remaining == 0:
            self.on_break = not self.on_break
            self.started = self.now()
            event = "break" if self.on_break else "work"
            remaining = (break_minutes if self.on_break else work_minutes) * 60
        return remaining, event
