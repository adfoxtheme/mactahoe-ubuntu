import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import Clutter from 'gi://Clutter';
import St from 'gi://St';

import { ClockWidget } from './modules/clockWidget.js';
import { WeatherWidget } from './modules/weatherWidget.js';
import { SystemWidget } from './modules/systemWidget.js';
import { LunarWidget } from './modules/lunarWidget.js';
import { RestWidget } from './modules/restWidget.js';

export default class UbuntuTahoeWidgetsExtension extends Extension {
    enable() {
        console.log('[UbuntuTahoeWidgets] Enabling macOS Tahoe Widgets extension...');
        this._settings = this.getSettings();

        // Right column stack
        this._stackBox = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            style: 'spacing: 12px;',
            reactive: false,
        });

        // Add to desktop background group
        Main.layoutManager._backgroundGroup.add_child(this._stackBox);

        // Build widgets based on settings
        this._buildWidgets();

        // Position widgets
        this._relayout();

        // Monitor changes
        this._monitorsChangedId = Main.layoutManager.connect('monitors-changed', () => this._relayout());

        // Overview show/hide animations
        this._overviewShowingId = Main.overview.connect('showing', () => {
            if (this._clockWidget) {
                this._clockWidget.ease({
                    opacity: 0,
                    duration: 200,
                    mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                });
            }
            this._stackBox.ease({
                opacity: 0,
                duration: 200,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            });
        });

        this._overviewHiddenId = Main.overview.connect('hidden', () => {
            if (this._clockWidget) {
                this._clockWidget.ease({
                    opacity: 255,
                    duration: 200,
                    mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                });
            }
            this._stackBox.ease({
                opacity: 255,
                duration: 200,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            });
        });

        // Watch settings changes
        this._settingsChangedIds = [
            this._settings.connect('changed::target-monitor', () => this._relayout()),
            this._settings.connect('changed::show-clock', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-weather', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-system', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-lunar', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-rest', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::clock-gap-x', () => this._relayout()),
            this._settings.connect('changed::clock-gap-y', () => this._relayout()),
            this._settings.connect('changed::stack-gap-x', () => this._relayout()),
            this._settings.connect('changed::stack-gap-y', () => this._relayout()),
        ];
    }

    _buildWidgets() {
        // Clock
        if (this._settings.get_boolean('show-clock')) {
            if (!this._clockWidget) {
                this._clockWidget = new ClockWidget();
                Main.layoutManager._backgroundGroup.add_child(this._clockWidget);
            }
        } else if (this._clockWidget) {
            this._clockWidget.destroy();
            this._clockWidget = null;
        }

        // Stack items in order: Weather, System, Lunar, Rest
        // 1. Weather
        if (this._settings.get_boolean('show-weather')) {
            if (!this._weatherWidget) {
                this._weatherWidget = new WeatherWidget(this._settings);
                this._stackBox.add_child(this._weatherWidget);
            }
        } else if (this._weatherWidget) {
            this._weatherWidget.destroy();
            this._weatherWidget = null;
        }

        // 2. System
        if (this._settings.get_boolean('show-system')) {
            if (!this._systemWidget) {
                this._systemWidget = new SystemWidget();
                this._stackBox.add_child(this._systemWidget);
            }
        } else if (this._systemWidget) {
            this._systemWidget.destroy();
            this._systemWidget = null;
        }

        // 3. Lunar
        if (this._settings.get_boolean('show-lunar')) {
            if (!this._lunarWidget) {
                this._lunarWidget = new LunarWidget();
                this._stackBox.add_child(this._lunarWidget);
            }
        } else if (this._lunarWidget) {
            this._lunarWidget.destroy();
            this._lunarWidget = null;
        }

        // 4. Rest
        if (this._settings.get_boolean('show-rest')) {
            if (!this._restWidget) {
                this._restWidget = new RestWidget();
                this._stackBox.add_child(this._restWidget);
            }
        } else if (this._restWidget) {
            this._restWidget.destroy();
            this._restWidget = null;
        }
    }

    _rebuildAndRelayout() {
        this._buildWidgets();
        this._relayout();
    }

    _getMonitor() {
        const target = this._settings.get_int('target-monitor');
        const monitors = Main.layoutManager.monitors;
        if (!monitors || monitors.length === 0)
            return Main.layoutManager.primaryMonitor;

        if (target === -1)
            return Main.layoutManager.primaryMonitor;

        // If specific monitor 0, 1, 2 is requested and exists
        if (target >= 0 && target < monitors.length)
            return monitors[target];

        // If target is 1 (second monitor) and there are at least 2 monitors
        if (target === 1 && monitors.length > 1) {
            const nonPrimary = monitors.find(m => m !== Main.layoutManager.primaryMonitor);
            if (nonPrimary) return nonPrimary;
        }

        return Main.layoutManager.primaryMonitor;
    }

    _relayout() {
        const monitor = this._getMonitor();
        if (!monitor) return;

        // Clock layout (left)
        if (this._clockWidget) {
            const clockGapX = this._settings.get_int('clock-gap-x');
            const clockGapY = this._settings.get_int('clock-gap-y');
            this._clockWidget.set_position(
                monitor.x + clockGapX,
                monitor.y + clockGapY
            );
        }

        // Stack layout (right)
        const stackGapX = this._settings.get_int('stack-gap-x');
        const stackGapY = this._settings.get_int('stack-gap-y');
        const stackWidth = 340;
        this._stackBox.set_position(
            monitor.x + monitor.width - stackWidth - stackGapX,
            monitor.y + stackGapY
        );
    }

    disable() {
        console.log('[UbuntuTahoeWidgets] Disabling macOS Tahoe Widgets extension...');

        if (this._monitorsChangedId) {
            Main.layoutManager.disconnect(this._monitorsChangedId);
            this._monitorsChangedId = null;
        }
        if (this._overviewShowingId) {
            Main.overview.disconnect(this._overviewShowingId);
            this._overviewShowingId = null;
        }
        if (this._overviewHiddenId) {
            Main.overview.disconnect(this._overviewHiddenId);
            this._overviewHiddenId = null;
        }

        if (this._settingsChangedIds) {
            this._settingsChangedIds.forEach(id => this._settings.disconnect(id));
            this._settingsChangedIds = [];
        }

        if (this._clockWidget) {
            this._clockWidget.destroy();
            this._clockWidget = null;
        }
        if (this._weatherWidget) {
            this._weatherWidget.destroy();
            this._weatherWidget = null;
        }
        if (this._systemWidget) {
            this._systemWidget.destroy();
            this._systemWidget = null;
        }
        if (this._lunarWidget) {
            this._lunarWidget.destroy();
            this._lunarWidget = null;
        }
        if (this._restWidget) {
            this._restWidget.destroy();
            this._restWidget = null;
        }

        if (this._stackBox) {
            this._stackBox.destroy();
            this._stackBox = null;
        }

        this._settings = null;
    }
}
