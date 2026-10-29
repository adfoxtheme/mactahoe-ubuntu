import { ExtensionPreferences } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Soup from 'gi://Soup?version=3.0';

const POPULAR_CITIES = [
    { name: 'Hà Nội', lat: 21.0285, lon: 105.8542 },
    { name: 'TP. Hồ Chí Minh', lat: 10.8230, lon: 106.6297 },
    { name: 'Đà Nẵng', lat: 16.0678, lon: 108.2208 },
    { name: 'Hải Phòng', lat: 20.8449, lon: 106.6881 },
    { name: 'Cần Thơ', lat: 10.0452, lon: 105.7469 },
    { name: 'Nha Trang (Khánh Hòa)', lat: 12.2388, lon: 109.1967 },
    { name: 'Đà Lạt (Lâm Đồng)', lat: 11.9404, lon: 108.4583 },
    { name: 'Huế', lat: 16.4637, lon: 107.5909 },
    { name: 'Quy Nhơn (Bình Định)', lat: 13.7820, lon: 109.2197 },
    { name: 'Vũng Tàu', lat: 10.3460, lon: 107.0843 },
    { name: 'Buôn Ma Thuột (Đắk Lắk)', lat: 12.6675, lon: 108.0383 },
    { name: 'Hạ Long (Quảng Ninh)', lat: 20.9505, lon: 107.0734 },
    { name: 'Phan Thiết (Bình Thuận)', lat: 10.9289, lon: 108.1021 },
    { name: 'Vinh (Nghệ An)', lat: 18.6734, lon: 105.6813 },
    { name: 'Thanh Hóa', lat: 19.8067, lon: 105.7852 },
    { name: 'Pleiku (Gia Lai)', lat: 13.9833, lon: 108.0000 },
];

export default class UbuntuTahoeWidgetsPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: 'Cài đặt Widget',
            icon_name: 'preferences-desktop-theme-symbolic',
        });
        window.add(page);

        // Group 1: Bật / Tắt từng Widget
        const widgetGroup = new Adw.PreferencesGroup({
            title: 'Bật / Tắt Widget',
            description: 'Tùy chỉnh các widget bạn muốn hiển thị trên màn hình desktop',
        });
        page.add(widgetGroup);

        const addSwitch = (title, subtitle, key) => {
            const row = new Adw.SwitchRow({
                title,
                subtitle,
            });
            settings.bind(key, row, 'active', Gio.SettingsBindFlags.DEFAULT);
            widgetGroup.add(row);
        };

        addSwitch('Đồng hồ lớn', 'Hiển thị đồng hồ số kính mờ bên trái màn hình', 'show-clock');
        addSwitch('Thời tiết', 'Dự báo nhiệt độ và thời tiết với icon MacTahoe', 'show-weather');
        addSwitch('Hệ thống', 'Giám sát CPU, GPU, RAM, SSD và mạng', 'show-system');
        addSwitch('Âm lịch', 'Lịch âm Việt Nam và can chi hôm nay', 'show-lunar');
        addSwitch('Nhắc nghỉ', 'Theo dõi thời gian và nhắc nhở nghỉ ngơi', 'show-rest');

        // Group 2: Chọn màn hình hiển thị
        const monitorGroup = new Adw.PreferencesGroup({
            title: 'Màn hình hiển thị Widget',
            description: 'Tùy chọn hiển thị widget trên màn hình chính hoặc màn hình thứ 2',
        });
        page.add(monitorGroup);

        const monitorModel = new Gtk.StringList();
        monitorModel.append('Màn hình chính (Primary Monitor)'); // 0 -> -1
        monitorModel.append('Màn hình thứ hai (Second Monitor)'); // 1 -> 1
        monitorModel.append('Màn hình 1 (Monitor 0)');           // 2 -> 0
        monitorModel.append('Màn hình 2 (Monitor 1)');           // 3 -> 1
        monitorModel.append('Màn hình 3 (Monitor 2)');           // 4 -> 2

        const monitorRow = new Adw.ComboRow({
            title: 'Màn hình hiển thị',
            subtitle: 'Chọn màn hình đặt đồng hồ lớn và cụm widget',
            model: monitorModel,
        });

        const curTarget = settings.get_int('target-monitor');
        if (curTarget === -1) monitorRow.selected = 0;
        else if (curTarget === 1) monitorRow.selected = 1;
        else if (curTarget === 0) monitorRow.selected = 2;
        else if (curTarget === 2) monitorRow.selected = 4;
        else monitorRow.selected = 0;

        monitorRow.connect('notify::selected', () => {
            let val;
            switch (monitorRow.selected) {
                case 0: val = -1; break; // Primary
                case 1: val = 1; break;  // 2nd monitor
                case 2: val = 0; break;  // Monitor 0
                case 3: val = 1; break;  // Monitor 1
                case 4: val = 2; break;  // Monitor 2
                default: val = -1; break;
            }
            settings.set_int('target-monitor', val);
        });
        monitorGroup.add(monitorRow);

        // Group 3: Cấu hình địa điểm & thời tiết
        const weatherGroup = new Adw.PreferencesGroup({
            title: 'Vị trí & Thời tiết',
            description: 'Chọn thành phố hoặc tìm kiếm địa điểm để cập nhật tọa độ chính xác',
        });
        page.add(weatherGroup);

        // Tọa độ hiện tại
        const coordRow = new Adw.ActionRow({
            title: 'Thành phố & Tọa độ dự báo',
            subtitle: `${settings.get_string('weather-city')} (Lat: ${settings.get_double('weather-lat').toFixed(4)}, Lon: ${settings.get_double('weather-lon').toFixed(4)})`,
        });
        weatherGroup.add(coordRow);

        const updateCoordSubtitle = () => {
            coordRow.subtitle = `${settings.get_string('weather-city')} (Lat: ${settings.get_double('weather-lat').toFixed(4)}, Lon: ${settings.get_double('weather-lon').toFixed(4)})`;
        };

        // 1. Combobox chọn nhanh thành phố
        const cityModel = new Gtk.StringList();
        let selectedIdx = -1;
        const currentCity = settings.get_string('weather-city');
        POPULAR_CITIES.forEach((c, idx) => {
            cityModel.append(c.name);
            if (c.name.toLowerCase() === currentCity.toLowerCase()) {
                selectedIdx = idx;
            }
        });
        cityModel.append('Tùy chỉnh (Tìm kiếm bên dưới)');
        if (selectedIdx === -1) selectedIdx = POPULAR_CITIES.length;

        const cityComboRow = new Adw.ComboRow({
            title: 'Chọn nhanh thành phố (Việt Nam)',
            subtitle: 'Tự động gán kinh độ và vĩ độ chính xác cho thành phố đã chọn',
            model: cityModel,
            selected: selectedIdx,
        });

        cityComboRow.connect('notify::selected', () => {
            const idx = cityComboRow.selected;
            if (idx < POPULAR_CITIES.length) {
                const item = POPULAR_CITIES[idx];
                settings.set_string('weather-city', item.name);
                settings.set_double('weather-lat', item.lat);
                settings.set_double('weather-lon', item.lon);
                updateCoordSubtitle();
            }
        });
        weatherGroup.add(cityComboRow);

        // 2. Tìm kiếm địa điểm bất kỳ (Geocoding API)
        const searchRow = new Adw.EntryRow({
            title: 'Tìm kiếm địa điểm bất kỳ (Toàn cầu)',
            text: currentCity,
            show_apply_button: true,
        });

        const session = new Soup.Session();
        searchRow.connect('apply', () => {
            const query = searchRow.text.trim();
            if (!query) return;

            searchRow.title = 'Đang tìm kiếm tọa độ...';
            const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=1&language=vi&format=json`;
            const msg = Soup.Message.new('GET', url);
            msg.request_headers.append('User-Agent', 'UbuntuTahoeWidgetsPrefs/1.0');

            session.send_and_read_async(msg, GLib.PRIORITY_DEFAULT, null, (src, res) => {
                try {
                    const bytes = session.send_and_read_finish(res);
                    const dec = new TextDecoder('utf-8');
                    const data = JSON.parse(dec.decode(bytes.toArray()));
                    if (data && data.results && data.results.length > 0) {
                        const hit = data.results[0];
                        const displayName = hit.name + (hit.country ? `, ${hit.country}` : '');
                        settings.set_string('weather-city', hit.name);
                        settings.set_double('weather-lat', hit.latitude);
                        settings.set_double('weather-lon', hit.longitude);
                        updateCoordSubtitle();
                        searchRow.title = `Đã cập nhật: ${displayName}`;
                        cityComboRow.selected = POPULAR_CITIES.length; // Custom
                    } else {
                        searchRow.title = 'Không tìm thấy địa điểm, hãy thử lại!';
                    }
                } catch (e) {
                    searchRow.title = 'Lỗi kết nối khi tìm kiếm!';
                }
            });
        });
        weatherGroup.add(searchRow);

        // 3. OpenWeather API Key (Tùy chọn)
        const apiKeyRow = new Adw.EntryRow({
            title: 'OpenWeather API Key (Tùy chọn)',
            text: settings.get_string('weather-api-key'),
            show_apply_button: true,
        });
        apiKeyRow.connect('apply', () => {
            settings.set_string('weather-api-key', apiKeyRow.text.trim());
        });
        weatherGroup.add(apiKeyRow);

        // 4. Chu kỳ làm mới
        const intervalRow = new Adw.SpinRow({
            title: 'Chu kỳ cập nhật (phút)',
            subtitle: 'Thời gian tự động làm mới dữ liệu thời tiết',
            adjustment: new Gtk.Adjustment({
                lower: 5,
                upper: 120,
                step_increment: 5,
                value: settings.get_int('weather-update-interval'),
            }),
        });
        settings.bind('weather-update-interval', intervalRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        weatherGroup.add(intervalRow);

        // Group 4: Vị trí và Căn lề
        const posGroup = new Adw.PreferencesGroup({
            title: 'Vị trí và Căn lề',
            description: 'Khoảng cách hiển thị widget trên màn hình desktop',
        });
        page.add(posGroup);

        const addSpin = (title, key, lower, upper, step) => {
            const row = new Adw.SpinRow({
                title,
                adjustment: new Gtk.Adjustment({
                    lower,
                    upper,
                    step_increment: step,
                    page_increment: step * 5,
                    value: settings.get_int(key),
                }),
            });
            settings.bind(key, row, 'value', Gio.SettingsBindFlags.DEFAULT);
            posGroup.add(row);
        };

        addSpin('Khoảng cách lề trái đồng hồ (px)', 'clock-gap-x', 0, 1000, 10);
        addSpin('Khoảng cách lề trên đồng hồ (px)', 'clock-gap-y', 0, 1000, 10);
        addSpin('Khoảng cách lề phải cụm widget (px)', 'stack-gap-x', 0, 1000, 10);
        addSpin('Khoảng cách lề trên cụm widget (px)', 'stack-gap-y', 0, 1000, 10);
    }
}
