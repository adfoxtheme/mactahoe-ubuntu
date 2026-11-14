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
        this._updateWidgetParents();

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
            for (const widget of [this._weatherWidget, this._systemWidget, this._lunarWidget, this._restWidget]) {
                if (!widget) continue;
                widget.ease({
                    opacity: 0,
                    duration: 200,
                    mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                });
            }
        });

        this._overviewHiddenId = Main.overview.connect('hidden', () => {
            if (this._clockWidget) {
                this._clockWidget.ease({
                    opacity: 255,
                    duration: 200,
                    mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                });
            }
            for (const widget of [this._weatherWidget, this._systemWidget, this._lunarWidget, this._restWidget]) {
                if (!widget) continue;
                widget.ease({
                    opacity: 255,
                    duration: 200,
                    mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                });
            }
        });

        // Watch settings changes
        this._settingsChangedIds = [
            this._settings.connect('changed::show-clock', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-weather', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-system', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-lunar', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::show-rest', () => this._rebuildAndRelayout()),
            this._settings.connect('changed::position-mode', () => {
                this._updateWidgetParents();
                this._relayout();
            }),
            this._settings.connect('changed::clock-gap-x', () => this._relayout()),
            this._settings.connect('changed::clock-gap-y', () => this._relayout()),
            this._settings.connect('changed::stack-gap-x', () => this._relayout()),
            this._settings.connect('changed::stack-gap-y', () => this._relayout()),
            this._settings.connect('changed::widget-clock-x', () => this._relayout()),
            this._settings.connect('changed::widget-clock-y', () => this._relayout()),
            this._settings.connect('changed::widget-weather-x', () => this._relayout()),
            this._settings.connect('changed::widget-weather-y', () => this._relayout()),
            this._settings.connect('changed::widget-system-x', () => this._relayout()),
            this._settings.connect('changed::widget-system-y', () => this._relayout()),
            this._settings.connect('changed::widget-lunar-x', () => this._relayout()),
            this._settings.connect('changed::widget-lunar-y', () => this._relayout()),
            this._settings.connect('changed::widget-rest-x', () => this._relayout()),
            this._settings.connect('changed::widget-rest-y', () => this._relayout()),
            this._settings.connect('changed::ui-language', () => {
                this._weatherWidget?.refreshWeather();
                this._systemWidget?.queue_repaint();
                this._lunarWidget?.queue_repaint();
                this._restWidget?.queue_repaint();
            }),
        ];
    }

    _addCardWidget(widget) {
        const parent = this._settings.get_string('position-mode') === 'individual'
            ? Main.layoutManager._backgroundGroup
            : this._stackBox;
        parent.add_child(widget);
    }

    _updateWidgetParents() {
        const individual = this._settings.get_string('position-mode') === 'individual';
        this._stackBox.visible = !individual;

        for (const widget of [this._weatherWidget, this._systemWidget, this._lunarWidget, this._restWidget]) {
            if (!widget) continue;

            const parent = widget.get_parent();
            const target = individual ? Main.layoutManager._backgroundGroup : this._stackBox;
            if (parent !== target) {
                parent.remove_child(widget);
                target.add_child(widget);
            }
        }
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
                this._addCardWidget(this._weatherWidget);
            }
        } else if (this._weatherWidget) {
            this._weatherWidget.destroy();
            this._weatherWidget = null;
        }

        // 2. System
        if (this._settings.get_boolean('show-system')) {
            if (!this._systemWidget) {
                this._systemWidget = new SystemWidget(this._settings);
                this._addCardWidget(this._systemWidget);
            }
        } else if (this._systemWidget) {
            this._systemWidget.destroy();
            this._systemWidget = null;
        }

        // 3. Lunar
        if (this._settings.get_boolean('show-lunar')) {
            if (!this._lunarWidget) {
                this._lunarWidget = new LunarWidget(this._settings);
                this._addCardWidget(this._lunarWidget);
            }
        } else if (this._lunarWidget) {
            this._lunarWidget.destroy();
            this._lunarWidget = null;
        }

        // 4. Rest
        if (this._settings.get_boolean('show-rest')) {
            if (!this._restWidget) {
                this._restWidget = new RestWidget(this._settings);
                this._addCardWidget(this._restWidget);
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

    _relayout() {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor) return;
        const individual = this._settings.get_string('position-mode') === 'individual';

        // Clock layout (left)
        if (this._clockWidget) {
            const clockGapX = this._settings.get_int(individual ? 'widget-clock-x' : 'clock-gap-x');
            const clockGapY = this._settings.get_int(individual ? 'widget-clock-y' : 'clock-gap-y');
            this._clockWidget.set_position(
                monitor.x + clockGapX,
                monitor.y + clockGapY
            );
        }

        if (individual) {
            const widgetPositions = [
                [this._weatherWidget, 'widget-weather-x', 'widget-weather-y'],
                [this._systemWidget, 'widget-system-x', 'widget-system-y'],
                [this._lunarWidget, 'widget-lunar-x', 'widget-lunar-y'],
                [this._restWidget, 'widget-rest-x', 'widget-rest-y'],
            ];
            for (const [widget, xKey, yKey] of widgetPositions) {
                if (!widget) continue;
                const rightMargin = this._settings.get_int(xKey);
                const topMargin = this._settings.get_int(yKey);
                widget.set_position(
                    monitor.x + monitor.width - widget.width - rightMargin,
                    monitor.y + topMargin
                );
            }
            return;
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
