import { ExtensionPreferences } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

export default class UbuntuTahoeWidgetsPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const language = settings.get_string('ui-language') ||
            (GLib.get_language_names().some(name => /^vi([_-]|$)/i.test(name)) ? 'vi' : 'en');
        const text = (vietnamese, english) => language === 'vi' ? vietnamese : english;

        const page = new Adw.PreferencesPage({
            title: text('Cài đặt Widget', 'Widget Settings'),
            icon_name: 'preferences-desktop-theme-symbolic',
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

        // Group 1: Widgets
        const widgetGroup = new Adw.PreferencesGroup({
            title: text('Bật / Tắt Widget', 'Widgets'),
            description: text(
                'Tùy chỉnh các widget bạn muốn hiển thị trên màn hình desktop',
                'Choose which widgets to show on the desktop'
            ),
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

        addSwitch(text('Đồng hồ lớn', 'Large clock'), text('Hiển thị đồng hồ số kính mờ bên trái màn hình', 'Show a frosted-glass digital clock on the left side of the desktop'), 'show-clock');
        addSwitch(text('Thời tiết', 'Weather'), text('Dự báo nhiệt độ và thời tiết với icon MacTahoe', 'Show the temperature and weather forecast with MacTahoe icons'), 'show-weather');
        addSwitch(text('Hệ thống', 'System'), text('Giám sát CPU, GPU, RAM, SSD và mạng', 'Monitor CPU, GPU, RAM, storage, and network usage'), 'show-system');
        addSwitch(text('Âm lịch', 'Lunar calendar'), text('Lịch âm Việt Nam và can chi hôm nay', 'Vietnamese lunar date and Can Chi for today'), 'show-lunar');
        addSwitch(text('Nhắc nghỉ', 'Break reminder'), text('Theo dõi thời gian và nhắc nhở nghỉ ngơi', 'Track uptime and remind you to take breaks'), 'show-rest');

        // Group 2: Weather settings
        const weatherGroup = new Adw.PreferencesGroup({
            title: text('Thời tiết (OpenWeatherMap)', 'Weather (OpenWeatherMap)'),
            description: text(
                'Cấu hình API OpenWeather (để trống sẽ dùng Open-Meteo miễn phí)',
                'Configure an OpenWeather API key; leave it blank to use free Open-Meteo'
            ),
        });
        page.add(weatherGroup);

        const apiKeyRow = new Adw.EntryRow({
            title: 'OpenWeather API Key',
            show_apply_button: true,
        });
        apiKeyRow.text = settings.get_string('weather-api-key');
        apiKeyRow.connect('apply', () => {
            settings.set_string('weather-api-key', apiKeyRow.text.trim());
        });
        weatherGroup.add(apiKeyRow);

        const cityRow = new Adw.EntryRow({
            title: text('Tên thành phố', 'City'),
            show_apply_button: true,
        });
        cityRow.text = settings.get_string('weather-city');
        cityRow.connect('apply', () => {
            settings.set_string('weather-city', cityRow.text.trim());
        });
        weatherGroup.add(cityRow);

        const intervalRow = new Adw.SpinRow({
            title: text('Chu kỳ cập nhật (phút)', 'Update interval (minutes)'),
            subtitle: text('Thời gian tự động làm mới dữ liệu thời tiết', 'How often to refresh weather data'),
            adjustment: new Gtk.Adjustment({
                lower: 5,
                upper: 120,
                step_increment: 5,
                value: settings.get_int('weather-update-interval'),
            }),
        });
        settings.bind('weather-update-interval', intervalRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        weatherGroup.add(intervalRow);

        // Group 3: Position and margins
        const posGroup = new Adw.PreferencesGroup({
            title: text('Vị trí và Căn lề', 'Position and margins'),
            description: text('Khoảng cách hiển thị widget trên màn hình desktop', 'Widget offsets from the desktop edges'),
        });
        page.add(posGroup);

        const addSpin = (title, key, lower, upper, step) => {
            const row = new Adw.SpinRow({
                title,
                adjustment: new Gtk.Adjustment({
                    lower,
                    upper,
                    step_increment: step,
                    value: settings.get_int(key),
                }),
            });
            settings.bind(key, row, 'value', Gio.SettingsBindFlags.DEFAULT);
            posGroup.add(row);
        };

        addSpin(text('Lề trái Đồng hồ (px)', 'Clock left margin (px)'), 'clock-gap-x', 0, 500, 10);
        addSpin(text('Lề trên Đồng hồ (px)', 'Clock top margin (px)'), 'clock-gap-y', 0, 500, 10);
        addSpin(text('Lề phải Cụm widget (px)', 'Widget group right margin (px)'), 'stack-gap-x', 0, 500, 10);
        addSpin(text('Lề trên Cụm widget (px)', 'Widget group top margin (px)'), 'stack-gap-y', 0, 500, 10);
    }
}
