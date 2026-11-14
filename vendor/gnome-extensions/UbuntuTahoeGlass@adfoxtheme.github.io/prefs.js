import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';
import GLib from 'gi://GLib';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

function readCustomMap(settings) {
    try {
        const raw = settings.get_string('application-custom-corner-radii');
        return JSON.parse(raw || '{}');
    } catch (e) {
        return {};
    }
}

function writeCustomMap(settings, map) {
    try {
        settings.set_string('application-custom-corner-radii', JSON.stringify(map));
    } catch (e) {}
}

export default class UbuntuTahoeGlassPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const language = settings.get_string('ui-language') ||
            (GLib.get_language_names().some(name => /^vi([_-]|$)/i.test(name)) ? 'vi' : 'en');
        const text = (vietnamese, english) => language === 'vi' ? vietnamese : english;

        const page = new Adw.PreferencesPage({
            title: text('Cài đặt', 'Settings'),
            icon_name: 'preferences-desktop-display-symbolic',
        });
        window.add(page);

        const languageGroup = new Adw.PreferencesGroup();
        const languageRow = new Adw.ComboRow({
            title: text('Ngôn ngữ', 'Language'),
            model: Gtk.StringList.new([
                text('Ngôn ngữ hệ thống', 'System default'),
                'Tiếng Việt',
                'English',
            ]),
        });
        languageRow.selected = settings.get_string('ui-language') === 'vi' ? 1 :
            settings.get_string('ui-language') === 'en' ? 2 : 0;
        languageRow.connect('notify::selected', () => {
            const value = ['', 'vi', 'en'][languageRow.selected];
            if (settings.get_string('ui-language') === value) return;
            settings.set_string('ui-language', value);
            window.remove(page);
            this.fillPreferencesWindow(window);
        });
        languageGroup.add(languageRow);
        page.add(languageGroup);

        // Group 1: Thanh Dock
        const dockGroup = new Adw.PreferencesGroup({
            title: text('Thanh Dock', 'Dock'),
            description: text(
                'Hiệu ứng kính lỏng cho UbuntuTahoeDock / Dash to Dock',
                'Liquid glass effect for UbuntuTahoeDock / Dash to Dock'
            ),
        });
        page.add(dockGroup);

        const dockSwitch = new Adw.SwitchRow({
            title: text('Bật kính lỏng cho Dock', 'Enable liquid glass for the Dock'),
            subtitle: text('Áp dụng shader kính lỏng phía sau thanh Dock', 'Apply the liquid-glass shader behind the Dock'),
        });
        settings.bind('enable-dock-glass', dockSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
        dockGroup.add(dockSwitch);

        const dockBlurRow = new Adw.SpinRow({
            title: text('Độ mờ nền (Blur Radius)', 'Background blur radius'),
            subtitle: text('Bán kính làm mờ phía sau kính (mặc định: 4)', 'Blur radius behind the glass (default: 4)'),
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 32,
                step_increment: 1,
            }),
        });
        settings.bind('dock-blur-radius', dockBlurRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        dockGroup.add(dockBlurRow);

        const dockCornerRow = new Adw.SpinRow({
            title: text('Bán kính bo góc (Corner Radius)', 'Corner radius'),
            subtitle: text('Độ bo cong các góc của kính dock (mặc định: 24)', 'Dock glass corner radius (default: 24)'),
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 60,
                step_increment: 1,
            }),
        });
        settings.bind('dock-corner-radius', dockCornerRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        dockGroup.add(dockCornerRow);

        // Group 2: Cửa sổ ứng dụng (Application Windows)
        const appGroup = new Adw.PreferencesGroup({
            title: text('Cửa sổ ứng dụng', 'Application windows'),
            description: text(
                'Hiệu ứng kính lỏng cho các cửa sổ ứng dụng (tự động nhận diện bo góc theo Theme đang dùng)',
                'Liquid-glass effect for application windows. Corner radii are detected from the active theme.'
            ),
        });
        page.add(appGroup);

        const appSwitch = new Adw.SwitchRow({
            title: text('Bật kính lỏng cho cửa sổ ứng dụng', 'Enable liquid glass for application windows'),
            subtitle: text('Áp dụng shader kính lỏng phía sau các cửa sổ ứng dụng', 'Apply the liquid-glass shader behind application windows'),
        });
        settings.bind('enable-application-glass', appSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(appSwitch);

        const allWindowsSwitch = new Adw.SwitchRow({
            title: text('Áp dụng cho tất cả cửa sổ', 'Apply to all windows'),
            subtitle: text('Bật hiệu ứng kính cho toàn bộ ứng dụng đang mở', 'Enable the glass effect for all open applications'),
        });
        settings.bind('application-glass-all-windows', allWindowsSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(allWindowsSwitch);

        const appOpacityRow = new Adw.SpinRow({
            title: text('Độ mờ đục nội dung', 'Content opacity'),
            subtitle: text(
                'Độ trong suốt của nội dung để hiệu ứng kính hiển thị xuyên qua (mặc định: 0.85)',
                'Content opacity controls how much of the glass effect shows through (default: 0.85)'
            ),
            adjustment: new Gtk.Adjustment({
                lower: 0.1,
                upper: 1.0,
                step_increment: 0.05,
                page_increment: 0.1,
            }),
            digits: 2,
        });
        settings.bind('application-content-opacity', appOpacityRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(appOpacityRow);

        const appBlurRow = new Adw.SpinRow({
            title: text('Độ mờ nền (Blur Radius)', 'Background blur radius'),
            subtitle: text('Bán kính làm mờ phía sau cửa sổ (mặc định: 12)', 'Blur radius behind windows (default: 12)'),
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 64,
                step_increment: 1,
            }),
        });
        settings.bind('application-blur-radius', appBlurRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(appBlurRow);

        const appCornerRadiusRow = new Adw.SpinRow({
            title: text('Góc bo cửa sổ chung', 'Global window corner radius'),
            subtitle: text(
                '0 = Tự động theo Theme (24px trong MacTahoe-Dark, 0px Terminals). Nhập > 0 để cố định toàn bộ.',
                '0 = follow the theme (24 px in MacTahoe-Dark, 0 px for terminals). Use a value above 0 to override all windows.'
            ),
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 60,
                step_increment: 1,
            }),
        });
        settings.bind('application-corner-radius', appCornerRadiusRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(appCornerRadiusRow);

        // Group 3: Tùy chỉnh góc bo riêng cho từng app
        const customGroup = new Adw.PreferencesGroup({
            title: text('Tùy chỉnh góc bo riêng theo ứng dụng', 'Per-application corner radius'),
            description: text(
                'Tự động bo thông minh theo đúng từng app: Chrome/VSCode/SSD bo cong 24px cạnh trên và 0px VUÔNG cạnh dưới; Terminal/Game vuông 0px; Libadwaita bo cả 4 góc. Bạn có thể ghi đè riêng từng app bên dưới:',
                'Corners are detected per app: Chrome/VS Code/SSD use 24 px top corners and square bottom corners; terminals and games use square corners; Libadwaita uses all four. Set per-app overrides below.'
            ),
        });
        page.add(customGroup);

        const createAppOverrideRow = (label, wmClass, defaultHint) => {
            const currentMap = readCustomMap(settings);
            const currentValue = currentMap[wmClass] !== undefined ? currentMap[wmClass] : -1;

            const row = new Adw.SpinRow({
                title: label,
                subtitle: text(
                    `WM_CLASS: "${wmClass}" (-1 = Tự động [${defaultHint}], 0 = Vuông hoàn toàn, hoặc nhập số px)`,
                    `WM_CLASS: "${wmClass}" (-1 = automatic [${defaultHint}], 0 = square, or enter a radius in px)`
                ),
                adjustment: new Gtk.Adjustment({
                    lower: -1,
                    upper: 60,
                    step_increment: 1,
                }),
            });
            row.set_value(currentValue);
            row.connect('notify::value', () => {
                const val = row.get_value();
                const map = readCustomMap(settings);
                if (val < 0) {
                    delete map[wmClass];
                } else {
                    map[wmClass] = val;
                }
                writeCustomMap(settings, map);
            });
            return row;
        };

        customGroup.add(createAppOverrideRow('Google Chrome', 'google-chrome', '24px'));
        customGroup.add(createAppOverrideRow('Mozilla Firefox', 'firefox', '24px'));
        customGroup.add(createAppOverrideRow('Visual Studio Code', 'code', '24px'));
        customGroup.add(createAppOverrideRow('Alacritty / Kitty', 'alacritty', '0px'));
    }
}
