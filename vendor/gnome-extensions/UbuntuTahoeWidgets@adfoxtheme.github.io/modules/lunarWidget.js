import St from 'gi://St';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Clutter from 'gi://Clutter';
import * as Drawing from './drawing.js';
import { getTodayLunar } from './lunarCalc.js';
import { getLanguage, textFor } from './language.js';

export const LunarWidget = GObject.registerClass(
class LunarWidget extends St.DrawingArea {
    _init(settings) {
        super._init({
            width: 340,
            height: 150,
            reactive: true,
            track_hover: true,
        });

        this._settings = settings;
        this._lunar = getTodayLunar();

        this.connect('repaint', this._onRepaint.bind(this));

        // Click to open GNOME Calendar
        this.connect('button-press-event', (actor, event) => {
            if (event.get_button() === 1) {
                try {
                    const app = Gio.AppInfo.create_from_commandline('gnome-calendar', null, Gio.AppInfoCreateFlags.NONE);
                    if (app) app.launch([], null);
                } catch (e) {
                    // ignore
                }
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });

        // Update every 30 minutes
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1800, () => {
            this._lunar = getTodayLunar();
            this.queue_repaint();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _onRepaint(area) {
        const cr = area.get_context();
        const width = 340;
        const height = 150;
        const l = this._lunar;

        // Card background
        Drawing.drawCard(
            cr, 0, 0, width, height, 24,
            [0.19, 0.14, 0.31, 0.97],
            [0.075, 0.065, 0.12, 0.98],
            0.16
        );

        // Crescent moon watermark in top right
        Drawing.drawMoonWatermark(cr, width - 30, 39, 30);

        const language = getLanguage(this._settings);
        Drawing.drawText(cr, 22, 29, textFor(language, 'Âm lịch', 'Lunar calendar'), 14, Drawing.COLORS.sysText, true, 'left', 'SF Pro Display');
        Drawing.drawText(cr, width - 22, 29, textFor(language, 'Hôm nay', 'Today'), 8.5, Drawing.COLORS.sysMuted, false, 'right');

        // Main Lunar Day
        Drawing.drawText(cr, 22, 87, String(l.lunarDay), 44, Drawing.COLORS.gold, true, 'left', 'SF Pro Display');

        // Month & Year title
        const monthLabel = language === 'vi'
            ? `Tháng ${l.lunarMonth}${l.lunarLeap ? ' nhuận' : ''} · ${l.yearName}`
            : `Month ${l.lunarMonth}${l.lunarLeap ? ' (leap)' : ''} · ${l.yearName}`;
        Drawing.drawText(cr, 94, 59, monthLabel, 13, Drawing.COLORS.sysText, true, 'left', 'SF Pro Display');
        Drawing.drawText(cr, 94, 78, textFor(language, 'Âm lịch hôm nay', 'Lunar date'), 9, Drawing.COLORS.sysSub, false);

        // Separator
        cr.setSourceRGBA(1, 1, 1, 0.10);
        cr.setLineWidth(1);
        cr.moveTo(22, 93);
        cr.lineTo(width - 22, 93);
        cr.stroke();

        // Solar date info
        const solarDateStr = `${String(l.solarDay).padStart(2, '0')}/${String(l.solarMonth).padStart(2, '0')}/${l.solarYear}  ·  ${l.weekday}`;
        Drawing.drawText(cr, 22, 112, textFor(language, 'Dương lịch', 'Solar date'), 8.5, Drawing.COLORS.sysMuted, false);
        Drawing.drawText(cr, 94, 112, solarDateStr, 9.2, Drawing.COLORS.sysSub, false);
    }

    destroy() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = null;
        }
        super.destroy();
    }
});
