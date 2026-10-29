import Soup from 'gi://Soup?version=3.0';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';

const session = new Soup.Session();

const ICON_BASE = GLib.get_home_dir() + '/.local/share/icons/MacTahoe-blue/status/32/';

function getIconPath(iconName) {
    const fullPath = ICON_BASE + iconName + '.svg';
    const file = Gio.File.new_for_path(fullPath);
    if (file.query_exists(null)) {
        return fullPath;
    }
    return ICON_BASE + 'weather-few-clouds.svg';
}

function mapOpenWeatherIcon(iconCode, conditionId) {
    const isNight = iconCode && iconCode.endsWith('n');
    
    // Group 2xx: Thunderstorm
    if (conditionId >= 200 && conditionId < 300) {
        return isNight ? 'weather-storm-night' : 'weather-storm';
    }
    // Group 3xx: Drizzle
    if (conditionId >= 300 && conditionId < 400) {
        return isNight ? 'weather-showers-scattered-night' : 'weather-showers-scattered';
    }
    // Group 5xx: Rain
    if (conditionId >= 500 && conditionId < 600) {
        if (conditionId === 511) return 'weather-freezing-rain';
        return isNight ? 'weather-showers-night' : 'weather-showers';
    }
    // Group 6xx: Snow
    if (conditionId >= 600 && conditionId < 700) {
        return isNight ? 'weather-snow-night' : 'weather-snow';
    }
    // Group 7xx: Atmosphere (Fog, Mist)
    if (conditionId >= 700 && conditionId < 800) {
        return 'weather-fog';
    }
    // Group 800: Clear
    if (conditionId === 800) {
        return isNight ? 'weather-clear-night' : 'weather-clear';
    }
    // Group 80x: Clouds
    if (conditionId === 801 || conditionId === 802) {
        return isNight ? 'weather-few-clouds-night' : 'weather-few-clouds';
    }
    return isNight ? 'weather-overcast-night' : 'weather-overcast';
}

const WMO_CODES = {
    0: ['Trời quang', 'weather-clear', 'weather-clear-night'],
    1: ['Ít mây', 'weather-few-clouds', 'weather-few-clouds-night'],
    2: ['Có mây', 'weather-few-clouds', 'weather-few-clouds-night'],
    3: ['Nhiều mây', 'weather-overcast', 'weather-overcast-night'],
    45: ['Sương mù', 'weather-fog', 'weather-fog'],
    48: ['Sương mù', 'weather-fog', 'weather-fog'],
    51: ['Mưa phùn nhẹ', 'weather-showers-scattered', 'weather-showers-scattered-night'],
    53: ['Mưa phùn', 'weather-showers', 'weather-showers-night'],
    55: ['Mưa phùn dày', 'weather-showers', 'weather-showers-night'],
    61: ['Mưa nhẹ', 'weather-showers-scattered', 'weather-showers-scattered-night'],
    63: ['Mưa vừa', 'weather-showers', 'weather-showers-night'],
    65: ['Mưa to', 'weather-showers', 'weather-showers-night'],
    71: ['Tuyết rơi nhẹ', 'weather-snow-scattered', 'weather-snow-scattered-night'],
    73: ['Tuyết rơi', 'weather-snow', 'weather-snow-night'],
    75: ['Tuyết dày', 'weather-snow', 'weather-snow-night'],
    80: ['Mưa rào nhẹ', 'weather-showers-scattered', 'weather-showers-scattered-night'],
    81: ['Mưa rào', 'weather-showers', 'weather-showers-night'],
    82: ['Mưa rào rất to', 'weather-showers', 'weather-showers-night'],
    95: ['Dông bão', 'weather-storm', 'weather-storm-night'],
    96: ['Dông kèm mưa đá nhẹ', 'weather-storm', 'weather-storm-night'],
    99: ['Dông kèm mưa đá to', 'weather-storm', 'weather-storm-night'],
};

function sendGetRequest(url) {
    return new Promise((resolve, reject) => {
        const message = Soup.Message.new('GET', url);
        message.request_headers.append('User-Agent', 'UbuntuTahoeWidgets/1.0');
        
        session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, null, (source, result) => {
            try {
                const bytes = session.send_and_read_finish(result);
                if (message.status_code !== 200) {
                    reject(new Error(`HTTP ${message.status_code}`));
                    return;
                }
                const decoder = new TextDecoder('utf-8');
                const text = decoder.decode(bytes.toArray());
                resolve(JSON.parse(text));
            } catch (err) {
                reject(err);
            }
        });
    });
}

export async function resolveCoordinates(cityName) {
    try {
        const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=5&language=vi&format=json`;
        const data = await sendGetRequest(url);
        if (data && data.results && data.results.length > 0) {
            return data.results.map(r => ({
                name: r.name,
                lat: r.latitude,
                lon: r.longitude,
                country: r.country || '',
                admin1: r.admin1 || '',
            }));
        }
    } catch (e) {
        console.warn('[UbuntuTahoeWidgets] Geocoding lookup error:', e.message);
    }
    return [];
}

export async function fetchWeather(settings) {
    const apiKey = (settings.weatherApiKey || '').trim();
    let city = (settings.weatherCity || 'Hà Nội').trim();
    let lat = settings.weatherLat ?? 21.0285;
    let lon = settings.weatherLon ?? 105.8542;

    const now = new Date();
    const weekdays = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
    const dateLabel = `${weekdays[now.getDay()]}, ${now.getDate()}/${now.getMonth() + 1}`;

    // 1. If OpenWeather API key is provided, try OpenWeatherMap
    if (apiKey.length > 0) {
        try {
            const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(city)}&appid=${apiKey}&units=metric&lang=vi`;
            const data = await sendGetRequest(url);

            const temp = Math.round(data.main.temp);
            const high = Math.round(data.main.temp_max);
            const low = Math.round(data.main.temp_min);
            const feels = Math.round(data.main.feels_like);
            const humidity = data.main.humidity;
            const wind = Math.round(data.wind.speed * 3.6); // m/s to km/h

            let condition = 'Trời quang';
            let iconName = 'weather-clear';
            if (data.weather && data.weather.length > 0) {
                const w = data.weather[0];
                condition = w.description ? (w.description.charAt(0).toUpperCase() + w.description.slice(1)) : 'Có mây';
                iconName = mapOpenWeatherIcon(w.icon, w.id);
            }

            return {
                city: data.name || city,
                date: dateLabel,
                temp: `${temp}`,
                high: `${high}`,
                low: `${low}`,
                feels: `${feels}`,
                humidity: `${humidity}`,
                wind: `${wind}`,
                condition,
                iconPath: getIconPath(iconName),
            };
        } catch (err) {
            console.warn('[UbuntuTahoeWidgets] OpenWeather failed, falling back to Open-Meteo:', err.message);
        }
    }

    // 2. Open-Meteo Mode (Free, no API key):
    // Check if coordinates need geocoding (e.g. if city name was changed but lat/lon still default Hanoi)
    const isDefaultHanoiCoords = Math.abs(lat - 21.0285) < 0.005 && Math.abs(lon - 105.8542) < 0.005;
    const isHanoiName = city.toLowerCase().includes('hà nội') || city.toLowerCase().includes('hanoi');
    if ((isDefaultHanoiCoords && !isHanoiName) || !lat || !lon) {
        const results = await resolveCoordinates(city);
        if (results.length > 0) {
            lat = results[0].lat;
            lon = results[0].lon;
            city = results[0].name;
            if (settings._settings && typeof settings._settings.set_double === 'function') {
                try {
                    settings._settings.set_double('weather-lat', lat);
                    settings._settings.set_double('weather-lon', lon);
                    settings._settings.set_string('weather-city', city);
                } catch (_) {}
            }
        }
    }

    // Fetch accurate forecast using exact latitude and longitude
    try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FHo_Chi_Minh`;
        const data = await sendGetRequest(url);

        const current = data.current;
        const daily = data.daily;

        const temp = Math.round(current.temperature_2m);
        const feels = Math.round(current.apparent_temperature);
        const humidity = Math.round(current.relative_humidity_2m);
        const wind = Math.round(current.wind_speed_10m);

        let high = '--';
        let low = '--';
        if (daily && daily.temperature_2m_max && daily.temperature_2m_max.length > 0) {
            high = Math.round(daily.temperature_2m_max[0]);
        }
        if (daily && daily.temperature_2m_min && daily.temperature_2m_min.length > 0) {
            low = Math.round(daily.temperature_2m_min[0]);
        }

        const code = current.weather_code || 0;
        const hour = now.getHours();
        const isNight = hour < 6 || hour >= 18;
        const entry = WMO_CODES[code] || ['Thời tiết tốt', 'weather-few-clouds', 'weather-few-clouds-night'];
        const condition = entry[0];
        const iconName = isNight ? entry[2] : entry[1];

        return {
            city,
            date: dateLabel,
            temp: `${temp}`,
            high: `${high}`,
            low: `${low}`,
            feels: `${feels}`,
            humidity: `${humidity}`,
            wind: `${wind}`,
            condition,
            iconPath: getIconPath(iconName),
        };
    } catch (err) {
        console.error('[UbuntuTahoeWidgets] Open-Meteo fallback also failed:', err);
        return {
            city,
            date: dateLabel,
            temp: '--',
            high: '--',
            low: '--',
            feels: '--',
            humidity: '--',
            wind: '--',
            condition: 'Chưa có mạng',
            iconPath: getIconPath('weather-few-clouds'),
        };
    }
}
