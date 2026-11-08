import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

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

        const page = new Adw.PreferencesPage({
            title: 'Cài đặt',
            icon_name: 'preferences-desktop-display-symbolic',
        });
        window.add(page);

        // Group 1: Thanh Dock
        const dockGroup = new Adw.PreferencesGroup({
            title: 'Thanh Dock',
            description: 'Hiệu ứng kính lỏng cho UbuntuTahoeDock / Dash to Dock',
        });
        page.add(dockGroup);

        const dockSwitch = new Adw.SwitchRow({
            title: 'Bật kính lỏng cho Dock',
            subtitle: 'Áp dụng shader kính lỏng phía sau thanh Dock',
        });
        settings.bind('enable-dock-glass', dockSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
        dockGroup.add(dockSwitch);

        const dockBlurRow = new Adw.SpinRow({
            title: 'Độ mờ nền (Blur Radius)',
            subtitle: 'Bán kính làm mờ phía sau kính (mặc định: 4)',
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 32,
                step_increment: 1,
            }),
        });
        settings.bind('dock-blur-radius', dockBlurRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        dockGroup.add(dockBlurRow);

        const dockCornerRow = new Adw.SpinRow({
            title: 'Bán kính bo góc (Corner Radius)',
            subtitle: 'Độ bo cong các góc của kính dock (mặc định: 24)',
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
            title: 'Cửa sổ ứng dụng (Application Windows)',
            description: 'Hiệu ứng kính lỏng cho các cửa sổ ứng dụng (tự động nhận diện bo góc theo Theme đang dùng)',
        });
        page.add(appGroup);

        const appSwitch = new Adw.SwitchRow({
            title: 'Bật kính lỏng cho cửa sổ ứng dụng',
            subtitle: 'Áp dụng shader kính lỏng phía sau các cửa sổ ứng dụng',
        });
        settings.bind('enable-application-glass', appSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(appSwitch);

        const allWindowsSwitch = new Adw.SwitchRow({
            title: 'Áp dụng cho tất cả cửa sổ',
            subtitle: 'Bật hiệu ứng kính cho toàn bộ ứng dụng đang mở',
        });
        settings.bind('application-glass-all-windows', allWindowsSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(allWindowsSwitch);

        const appOpacityRow = new Adw.SpinRow({
            title: 'Độ mờ đục nội dung (Content Opacity)',
            subtitle: 'Độ trong suốt của nội dung để hiệu ứng kính hiển thị xuyên qua (mặc định: 0.85)',
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
            title: 'Độ mờ nền (Blur Radius)',
            subtitle: 'Bán kính làm mờ phía sau cửa sổ (mặc định: 12)',
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 64,
                step_increment: 1,
            }),
        });
        settings.bind('application-blur-radius', appBlurRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        appGroup.add(appBlurRow);

        const appCornerRadiusRow = new Adw.SpinRow({
            title: 'Góc bo cửa sổ chung (Corner Radius)',
            subtitle: '0 = Tự động theo Theme (24px trong MacTahoe-Dark, 0px Terminals). Nhập > 0 để cố định toàn bộ.',
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
            title: 'Tùy chỉnh góc bo riêng theo app (Per-App Corner Radius)',
            description: 'Tự động bo thông minh theo đúng từng app: Chrome/VSCode/SSD bo cong 24px cạnh trên và 0px VUÔNG cạnh dưới; Terminal/Game vuông 0px; Libadwaita bo cả 4 góc. Bạn có thể ghi đè riêng từng app bên dưới:',
        });
        page.add(customGroup);

        const createAppOverrideRow = (label, wmClass, defaultHint) => {
            const currentMap = readCustomMap(settings);
            const currentValue = currentMap[wmClass] !== undefined ? currentMap[wmClass] : -1;

            const row = new Adw.SpinRow({
                title: label,
                subtitle: `WM_CLASS: "${wmClass}" (-1 = Tự động [${defaultHint}], 0 = Vuông hoàn toàn, hoặc nhập số px)`,
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
