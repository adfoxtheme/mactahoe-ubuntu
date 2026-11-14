import St from 'gi://St';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Clutter from 'gi://Clutter';
import * as Drawing from './drawing.js';
import { readSystemMetrics } from './systemMetrics.js';
import { getLanguage, textFor } from './language.js';

export const SystemWidget = GObject.registerClass(
class SystemWidget extends St.DrawingArea {
    _init(settings) {
        this._settings = settings;
        this._metrics = readSystemMetrics();
        const hasGpu = !!(this._metrics?.gpu?.hasGpu);
        const initHeight = hasGpu ? 300 : 258;

        super._init({
            width: 340,
            height: initHeight,
            reactive: true,
            track_hover: true,
        });

        this.connect('repaint', this._onRepaint.bind(this));

        // Click to open GNOME System Monitor
        this.connect('button-press-event', (actor, event) => {
            if (event.get_button() === 1) {
                try {
                    const app = Gio.AppInfo.create_from_commandline('gnome-system-monitor', null, Gio.AppInfoCreateFlags.NONE);
                    if (app) app.launch([], null);
                } catch (e) {
                    // ignore
                }
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });

        // 2-second update interval for responsive resource graphs
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
            this._metrics = readSystemMetrics();
            this._updateDimensions();
            this.queue_repaint();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _updateDimensions() {
        const hasGpu = !!(this._metrics?.gpu?.hasGpu);
        const targetHeight = hasGpu ? 300 : 258;
        if (this.height !== targetHeight) {
            this.height = targetHeight;
            this.queue_relayout();
        }
    }

    _onRepaint(area) {
        const cr = area.get_context();
        const width = 340;
        const m = this._metrics;
        const hasGpu = !!(m.gpu && m.gpu.hasGpu);
        const height = hasGpu ? 300 : 258;

        // Card Background
        Drawing.drawCard(
            cr, 0, 0, width, height, 26,
            [0.13, 0.13, 0.16, 0.95],
            [0.065, 0.065, 0.085, 0.97],
            0.15
        );

        const language = getLanguage(this._settings);
        Drawing.drawText(cr, 22, 33, textFor(language, 'Hệ thống', 'System'), 14, Drawing.COLORS.sysText, true, 'left', 'SF Pro Display');
        Drawing.drawText(cr, width - 22, 33, m.uptime, 8.2, Drawing.COLORS.sysMuted, false, 'right');

        // 1. CPU
        const cpuSub = m.cpu.model + (m.cpu.temp !== null ? `  •  ${m.cpu.temp}°C` : '');
        Drawing.drawSystemIcon(cr, 'cpu', 22, 51, Drawing.COLORS.blue);
        Drawing.drawText(cr, 44, 61, 'CPU', 9.5, Drawing.COLORS.sysSub, false);
        Drawing.drawText(cr, width - 22, 61, `${m.cpu.percent}%`, 10, Drawing.COLORS.sysText, true, 'right');
        Drawing.drawProgressBar(cr, 22, 69, width - 44, 6, m.cpu.percent, Drawing.COLORS.blue);
        Drawing.drawText(cr, 22, 86, cpuSub, 8.0, Drawing.COLORS.sysMuted, false);

        let yOffset = 93;

        // 2. GPU (only when discrete GPU present)
        if (hasGpu) {
            let gpuVal = `${m.gpu.util}%`;
            if (m.gpu.temp !== null) gpuVal += `  •  ${m.gpu.temp}°C`;
            let gpuSub = m.gpu.model || 'GPU';
            if (m.gpu.used && m.gpu.total) {
                gpuSub += `  •  ${m.gpu.used}/${m.gpu.total} MB`;
            }
            Drawing.drawSystemIcon(cr, 'gpu', 22, yOffset, Drawing.COLORS.green);
            Drawing.drawText(cr, 44, yOffset + 10, 'GPU', 9.5, Drawing.COLORS.sysSub, false);
            Drawing.drawText(cr, width - 22, yOffset + 10, gpuVal, 10, Drawing.COLORS.sysText, true, 'right');
            Drawing.drawProgressBar(cr, 22, yOffset + 18, width - 44, 6, m.gpu.util, Drawing.COLORS.green);
            Drawing.drawText(cr, 22, yOffset + 35, gpuSub, 8.0, Drawing.COLORS.sysMuted, false);
            yOffset += 42;
        }

        // 3. RAM
        const ramSub = `${m.ram.text}  •  ${textFor(language, 'Swap', 'Swap')} ${m.ram.swapPercent}%`;
        Drawing.drawSystemIcon(cr, 'ram', 22, yOffset, Drawing.COLORS.purple);
        Drawing.drawText(cr, 44, yOffset + 10, 'RAM', 9.5, Drawing.COLORS.sysSub, false);
        Drawing.drawText(cr, width - 22, yOffset + 10, `${m.ram.percent}%`, 10, Drawing.COLORS.sysText, true, 'right');
        Drawing.drawProgressBar(cr, 22, yOffset + 18, width - 44, 6, m.ram.percent, Drawing.COLORS.purple);
        Drawing.drawText(cr, 22, yOffset + 35, ramSub, 8.0, Drawing.COLORS.sysMuted, false);
        yOffset += 42;

        // 4. SSD
        Drawing.drawSystemIcon(cr, 'ssd', 22, yOffset, Drawing.COLORS.orange);
        Drawing.drawText(cr, 44, yOffset + 10, 'SSD', 9.5, Drawing.COLORS.sysSub, false);
        Drawing.drawText(cr, width - 22, yOffset + 10, `${m.disk.percent}%`, 10, Drawing.COLORS.sysText, true, 'right');
        Drawing.drawProgressBar(cr, 22, yOffset + 18, width - 44, 6, m.disk.percent, Drawing.COLORS.orange);
        Drawing.drawText(cr, 22, yOffset + 35, m.disk.text, 8.0, Drawing.COLORS.sysMuted, false);
        yOffset += 49;

        // Separator
        cr.setSourceRGBA(1, 1, 1, 0.08);
        cr.setLineWidth(1);
        cr.moveTo(22, yOffset);
        cr.lineTo(width - 22, yOffset);
        cr.stroke();
        yOffset += 9;

        // 5. Network
        Drawing.drawSystemIcon(cr, 'network', 22, yOffset, Drawing.COLORS.cyan);
        Drawing.drawText(cr, 44, yOffset + 10, textFor(language, 'Mạng', 'Network'), 9.5, Drawing.COLORS.sysSub, false);
        Drawing.drawText(cr, width - 22, yOffset + 10, `↓ ${m.net.downText}    ↑ ${m.net.upText}`, 9.0, Drawing.COLORS.sysText, true, 'right');
        Drawing.drawText(cr, 22, yOffset + 27, m.net.interface, 8.0, Drawing.COLORS.sysMuted, false);
    }

    destroy() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = null;
        }
        super.destroy();
    }
});
