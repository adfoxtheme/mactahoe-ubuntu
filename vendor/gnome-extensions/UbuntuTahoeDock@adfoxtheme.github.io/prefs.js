import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import { ExtensionPreferences } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class UbuntuTahoeDockPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: 'Cài đặt UbuntuTahoe Dock',
            icon_name: 'preferences-desktop-display-symbolic',
        });
        window.add(page);

        // Group 1: Chế độ hiển thị & Ẩn hiện
        const behaviorGroup = new Adw.PreferencesGroup({
            title: 'Chế độ hiển thị Dock',
            description: 'Tùy chỉnh hành vi ẩn hoặc giữ cố định thanh Dock trên màn hình',
        });
        page.add(behaviorGroup);

        const hideModeModel = new Gtk.StringList({
            strings: [
                'Ẩn khi ứng dụng full',
                'Luôn ẩn',
                'Luôn hiển thị',
            ],
        });

        const hideModeRow = new Adw.ComboRow({
            title: 'Hành vi thanh Dock',
            subtitle: 'Chọn cách thanh Dock xuất hiện khi làm việc với cửa sổ',
            model: hideModeModel,
        });
        behaviorGroup.add(hideModeRow);

        const getActiveModeIndex = () => {
            const dockFixed = settings.get_boolean('dock-fixed');
            const autohide = settings.get_boolean('autohide');
            const intellihide = settings.get_boolean('intellihide');
            const intellihideMode = settings.get_enum('intellihide-mode');

            if (dockFixed || (intellihide && intellihideMode === 3)) {
                return 2; // Luôn hiển thị (Nổi trên ứng dụng)
            } else if (autohide && intellihide) {
                return 0; // Ẩn khi ứng dụng full
            } else if (autohide && !intellihide) {
                return 1; // Luôn ẩn
            } else {
                return 0;
            }
        };

        const applyModeIndex = index => {
            if (index === 0) {
                // Ẩn khi ứng dụng full
                settings.set_boolean('dock-fixed', false);
                settings.set_boolean('autohide', true);
                settings.set_boolean('intellihide', true);
                settings.set_enum('intellihide-mode', 2); // MAXIMIZED_WINDOWS
            } else if (index === 1) {
                // Luôn ẩn
                settings.set_boolean('dock-fixed', false);
                settings.set_boolean('autohide', true);
                settings.set_boolean('intellihide', false);
            } else if (index === 2) {
                // Luôn hiển thị nổi trên ứng dụng (không làm co cửa sổ hay để khoảng trống bên dưới)
                settings.set_boolean('dock-fixed', false);
                settings.set_boolean('autohide', true);
                settings.set_boolean('intellihide', true);
                settings.set_enum('intellihide-mode', 3); // ALWAYS_ON_TOP
            }
        };

        let updating = false;
        hideModeRow.selected = getActiveModeIndex();

        hideModeRow.connect('notify::selected', () => {
            if (updating) return;
            updating = true;
            applyModeIndex(hideModeRow.selected);
            updating = false;
        });

        const updateRow = () => {
            if (updating) return;
            updating = true;
            hideModeRow.selected = getActiveModeIndex();
            updating = false;
        };

        settings.connect('changed::dock-fixed', updateRow);
        settings.connect('changed::autohide', updateRow);
        settings.connect('changed::intellihide', updateRow);
        settings.connect('changed::intellihide-mode', updateRow);

        // Group 2: Kích thước Dock
        const group = new Adw.PreferencesGroup({
            title: 'Kích thước Dock',
            description: 'Kéo thanh trượt qua lại để tùy chỉnh độ lớn biểu tượng trên thanh Dock',
        });
        page.add(group);

        const iconSizeRow = new Adw.ActionRow({
            title: 'Kích thước biểu tượng',
            subtitle: 'Mặc định chuẩn macOS Tahoe là 45px',
        });

        const scale = new Gtk.Scale({
            orientation: Gtk.Orientation.HORIZONTAL,
            adjustment: new Gtk.Adjustment({
                lower: 24,
                upper: 96,
                step_increment: 1,
                page_increment: 5,
                value: settings.get_int('dash-max-icon-size') || 45,
            }),
            digits: 0,
            draw_value: true,
            hexpand: true,
            valign: Gtk.Align.CENTER,
        });

        scale.set_size_request(240, -1);

        scale.connect('value-changed', () => {
            const val = Math.round(scale.get_value());
            if (settings.get_int('dash-max-icon-size') !== val) {
                settings.set_int('dash-max-icon-size', val);
            }
        });

        settings.connect('changed::dash-max-icon-size', () => {
            const val = settings.get_int('dash-max-icon-size');
            if (scale.get_value() !== val) {
                scale.set_value(val);
            }
        });

        iconSizeRow.add_suffix(scale);
        group.add(iconSizeRow);

        // Group 2: Màn hình hiển thị Dock (Multi-monitor)
        const monitorGroup = new Adw.PreferencesGroup({
            title: 'Màn hình hiển thị Dock',
            description: 'Tùy chọn hiển thị thanh Dock trên màn hình chính, màn hình phụ hoặc cả 2 màn hình',
        });
        page.add(monitorGroup);

        const multiMonitorRow = new Adw.SwitchRow({
            title: 'Hiển thị Dock trên tất cả màn hình (Multi-monitor)',
            subtitle: 'Bật để hiện thanh Dock trên cả màn hình chính và màn hình thứ 2',
        });
        settings.bind('multi-monitor', multiMonitorRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        monitorGroup.add(multiMonitorRow);

        const monitorModel = new Gtk.StringList();
        monitorModel.append('Màn hình chính (Primary Monitor)'); // -1
        monitorModel.append('Màn hình 1');                        // 0
        monitorModel.append('Màn hình 2 (Second Monitor)');      // 1

        const dockMonitorRow = new Adw.ComboRow({
            title: 'Màn hình chỉ định (nếu không hiện tất cả)',
            subtitle: 'Chọn màn hình đặt Dock khi tắt chế độ hiện trên tất cả màn hình',
            model: monitorModel,
        });

        const curDockMon = settings.get_int('preferred-monitor');
        if (curDockMon === 0) dockMonitorRow.selected = 1;
        else if (curDockMon === 1) dockMonitorRow.selected = 2;
        else dockMonitorRow.selected = 0;

        dockMonitorRow.connect('notify::selected', () => {
            let val;
            switch (dockMonitorRow.selected) {
                case 1: val = 0; break;
                case 2: val = 1; break;
                default: val = -1; break;
            }
            settings.set_int('preferred-monitor', val);
        });
        monitorGroup.add(dockMonitorRow);

        const isolateRow = new Adw.SwitchRow({
            title: 'Tách biệt ứng dụng theo màn hình (Isolate Monitors)',
            subtitle: 'Chỉ hiển thị trên Dock các cửa sổ ứng dụng đang mở trên màn hình đó',
        });
        settings.bind('isolate-monitors', isolateRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        monitorGroup.add(isolateRow);
    }
}
