import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import { ExtensionPreferences } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class UbuntuTahoeDockPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const language = settings.get_string('ui-language') ||
            (GLib.get_language_names().some(name => /^vi([_-]|$)/i.test(name)) ? 'vi' : 'en');
        const text = (vietnamese, english) => language === 'vi' ? vietnamese : english;

        const page = new Adw.PreferencesPage({
            title: text('Cài đặt UbuntuTahoe Dock', 'UbuntuTahoe Dock Settings'),
            icon_name: 'preferences-desktop-display-symbolic',
        });
        window.add(page);

        const languageGroup = new Adw.PreferencesGroup();
        const languageModel = Gtk.StringList.new([
            text('Ngôn ngữ hệ thống', 'System default'),
            'Tiếng Việt',
            'English',
        ]);
        const languageRow = new Adw.ComboRow({
            title: text('Ngôn ngữ', 'Language'),
            model: languageModel,
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

        // Group 1: Visibility
        const behaviorGroup = new Adw.PreferencesGroup({
            title: text('Chế độ hiển thị Dock', 'Dock visibility'),
            description: text(
                'Tùy chỉnh hành vi ẩn hoặc giữ cố định thanh Dock trên màn hình',
                'Choose when the Dock hides or stays visible on screen'
            ),
        });
        page.add(behaviorGroup);

        const hideModeModel = new Gtk.StringList({
            strings: [
                text('Ẩn khi ứng dụng phóng to', 'Hide when a window is maximized'),
                text('Luôn ẩn', 'Always hidden'),
                text('Luôn hiển thị', 'Always visible'),
            ],
        });

        const hideModeRow = new Adw.ComboRow({
            title: text('Hành vi thanh Dock', 'Dock behavior'),
            subtitle: text(
                'Chọn cách thanh Dock xuất hiện khi làm việc với cửa sổ',
                'Choose how the Dock behaves while working with windows'
            ),
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

        // Group 2: Dock size
        const group = new Adw.PreferencesGroup({
            title: text('Kích thước Dock', 'Dock size'),
            description: text(
                'Kéo thanh trượt qua lại để tùy chỉnh độ lớn biểu tượng trên thanh Dock',
                'Adjust the size of icons in the Dock'
            ),
        });
        page.add(group);

        const iconSizeRow = new Adw.ActionRow({
            title: text('Kích thước biểu tượng', 'Icon size'),
            subtitle: text('Mặc định chuẩn macOS Tahoe là 45px', 'The macOS Tahoe default is 45 px'),
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
    }
}
