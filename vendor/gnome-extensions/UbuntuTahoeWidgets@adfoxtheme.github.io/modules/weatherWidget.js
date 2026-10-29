import St from 'gi://St';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Clutter from 'gi://Clutter';
import * as Drawing from './drawing.js';
import { fetchWeather } from './openweather.js';

export const WeatherWidget = GObject.registerClass(
class WeatherWidget extends St.DrawingArea {
    _init(settings) {
        super._init({
            width: 340,
            height: 210,
            reactive: true,
            track_hover: true,
        });

        this._settings = settings;
        this._weatherData = {
            city: settings.get_string('weather-city') || 'Hà Nội',
            date: 'Đang tải…',
            temp: '--',
            high: '--',
            low: '--',
            feels: '--',
            humidity: '--',
            wind: '--',
            condition: 'Đang kết nối…',
            iconPath: null,
        };

        this.connect('repaint', this._onRepaint.bind(this));

        // Click to refresh or open weather
        this.connect('button-press-event', (actor, event) => {
            if (event.get_button() === 1) { // Left click
                this.refreshWeather();
                try {
                    const app = Gio.AppInfo.get_default_for_type('x-scheme-handler/weather', false);
                    if (app) app.launch([], null);
                } catch (e) {
                    // ignore
                }
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });

        this.refreshWeather();

        // Interval
        const intervalMinutes = Math.max(5, settings.get_int('weather-update-interval') || 15);
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, intervalMinutes * 60, () => {
            this.refreshWeather();
            return GLib.SOURCE_CONTINUE;
        });

        // Listen for setting changes
        this._cityChangeId = settings.connect('changed::weather-city', () => this.refreshWeather());
        this._apiKeyChangeId = settings.connect('changed::weather-api-key', () => this.refreshWeather());
    }

    async refreshWeather() {
        try {
            const data = await fetchWeather({
                weatherApiKey: this._settings.get_string('weather-api-key'),
                weatherCity: this._settings.get_string('weather-city'),
                weatherLat: this._settings.get_double('weather-lat'),
                weatherLon: this._settings.get_double('weather-lon'),
                _settings: this._settings,
            });
            this._weatherData = data;
            this.queue_repaint();
        } catch (e) {
            console.error('[UbuntuTahoeWidgets] Error refreshing weather:', e);
        }
    }

    _onRepaint(area) {
        const cr = area.get_context();
        const width = 340;
        const height = 210;

        // Card background with blue gradient and sheen
        Drawing.drawCard(
            cr, 0, 0, width, height, 26,
            [0.10, 0.30, 0.62, 0.97],
            [0.34, 0.63, 0.96, 0.97],
            0.20
        );

        // Halo circle behind icon
        cr.setSourceRGBA(1, 1, 1, 0.07);
        cr.arc(width - 72, 64, 52, 0, 2 * Math.PI);
        cr.fill();

        // Weather text
        const d = this._weatherData;
        Drawing.drawText(cr, 22, 33, d.city || 'Hà Nội', 14, Drawing.COLORS.white, true, 'left', 'SF Pro Display');
        Drawing.drawText(cr, 22, 50, d.date || '', 9, Drawing.COLORS.weatherSub, false, 'left');

        Drawing.drawText(cr, 22, 111, (d.temp || '--') + '°', 52, Drawing.COLORS.white, true, 'left', 'SF Pro Display');
        Drawing.drawText(cr, 22, 132, d.condition || 'Đang tải…', 11.5, Drawing.COLORS.weatherSub, false);

        Drawing.drawText(
            cr, 22, 154,
            `H:${d.high || '--'}°    L:${d.low || '--'}°`,
            10, Drawing.COLORS.weatherSub, false
        );

        Drawing.drawText(
            cr, 22, 174,
            `Cảm giác ${d.feels || '--'}°   •   Độ ẩm ${d.humidity || '--'}%   •   Gió ${d.wind || '--'} km/h`,
            8.2, Drawing.COLORS.weatherMuted, false
        );

        // Icon
        if (d.iconPath) {
            Drawing.drawImage(cr, d.iconPath, width - 122, 16, 96);
        }
    }

    destroy() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = null;
        }
        if (this._cityChangeId) {
            this._settings.disconnect(this._cityChangeId);
            this._cityChangeId = null;
        }
        if (this._apiKeyChangeId) {
            this._settings.disconnect(this._apiKeyChangeId);
            this._apiKeyChangeId = null;
        }
        super.destroy();
    }
});
