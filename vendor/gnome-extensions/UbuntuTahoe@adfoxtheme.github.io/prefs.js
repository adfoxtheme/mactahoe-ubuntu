import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import { ExtensionPreferences } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class UbuntuTahoePreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: 'Thanh Shell & Giao diện Tahoe',
            icon_name: 'preferences-desktop-display-symbolic',
        });
        window.add(page);

        // Group 1: Thanh Shell trên cùng (Top Panel)
        const panelGroup = new Adw.PreferencesGroup({
            title: 'Thanh Shell trên cùng (Top Panel)',
            description: 'Tùy chỉnh bố cục đồng hồ, menu ứng dụng và nút hoạt động',
        });
        page.add(panelGroup);

        // 1. Vị trí Đồng hồ & Thông báo
        const clockModel = new Gtk.StringList();
        clockModel.append('Ở giữa (Mặc định GNOME)');           // 0
        clockModel.append('Bên phải (Phong cách macOS Tahoe)'); // 1
        clockModel.append('Bên trái');                          // 2
        clockModel.append('Giữ nguyên bản (Không can thiệp)');  // 3 -> mapped to -1

        const clockRow = new Adw.ComboRow({
            title: 'Vị trí Đồng hồ & Cụm thông báo',
            subtitle: 'Chọn nơi hiển thị ngày giờ và thông báo trên thanh panel',
            model: clockModel,
        });

        const currentPos = settings.get_int('clock-position');
        if (currentPos === 0) clockRow.selected = 0;
        else if (currentPos === 1) clockRow.selected = 1;
        else if (currentPos === 2) clockRow.selected = 2;
        else clockRow.selected = 3;

        clockRow.connect('notify::selected', () => {
            let val;
            switch (clockRow.selected) {
                case 0: val = 0; break;
                case 1: val = 1; break;
                case 2: val = 2; break;
                default: val = -1; break;
            }
            settings.set_int('clock-position', val);
        });
        panelGroup.add(clockRow);

        // 2. Global Menu (File / Edit / View / Go)
        const globalMenuRow = new Adw.SwitchRow({
            title: 'Menu ứng dụng toàn cục (Global Menu)',
            subtitle: 'Hiển thị cụm File/Edit/View/Go trên panel (Tắt nếu muốn menu nằm trong cửa sổ ứng dụng)',
        });
        settings.bind('enable-globalmenu', globalMenuRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        panelGroup.add(globalMenuRow);

        // 3. Ẩn nút Hoạt động (Activities)
        const activitiesRow = new Adw.SwitchRow({
            title: 'Ẩn nút Hoạt động (Activities)',
            subtitle: 'Tắt để hiển thị nút Hoạt động như mặc định của GNOME',
        });
        settings.bind('hide-activities', activitiesRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        panelGroup.add(activitiesRow);

        // Group 2: Hiệu ứng giao diện
        const effectGroup = new Adw.PreferencesGroup({
            title: 'Hiệu ứng giao diện',
            description: 'Tùy chỉnh hiệu ứng mờ kính và các thành phần bổ trợ',
        });
        page.add(effectGroup);

        // 4. Blur
        const blurRow = new Adw.SwitchRow({
            title: 'Hiệu ứng kính mờ (Blur)',
            subtitle: 'Làm mờ nền kính Overview và thư mục ứng dụng',
        });
        settings.bind('enable-blur', blurRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        effectGroup.add(blurRow);

        // 5. Kimpanel
        const kimRow = new Adw.SwitchRow({
            title: 'Bảng ứng viên gõ phím (Kimpanel)',
            subtitle: 'Hiển thị bảng chọn từ gõ tiếng Việt / bộ gõ IBus trên panel',
        });
        settings.bind('enable-kimpanel', kimRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        effectGroup.add(kimRow);
    }
}
