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

        const modeGroup = new Adw.PreferencesGroup({
            title: text('Chế độ vị trí', 'Position mode'),
            description: text(
                'Chọn vị trí dùng chung cho nhóm hoặc đặt riêng từng widget',
                'Use one shared position for the group or position each widget separately'
            ),
        });
        page.add(modeGroup);

        const modeRow = new Adw.ComboRow({
            title: text('Kiểu bố trí', 'Layout'),
            model: Gtk.StringList.new([
                text('Theo nhóm', 'Group'),
                text('Từng widget', 'Individual widgets'),
            ]),
        });
        modeRow.selected = settings.get_string('position-mode') === 'individual' ? 1 : 0;
        modeGroup.add(modeRow);

        // Group 3: Group position and margins
        const posGroup = new Adw.PreferencesGroup({
            title: text('Vị trí nhóm', 'Group position'),
            description: text(
                'Điều chỉnh vị trí đồng hồ và toàn bộ nhóm thẻ tiện ích',
                'Set the clock and the position of the widget card group'
            ),
        });
        page.add(posGroup);

        const addSpin = (group, title, key, lower, upper, step) => {
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
            group.add(row);
        };

        addSpin(posGroup, text('Lề trái Đồng hồ (px)', 'Clock left margin (px)'), 'clock-gap-x', 0, 500, 10);
        addSpin(posGroup, text('Lề trên Đồng hồ (px)', 'Clock top margin (px)'), 'clock-gap-y', 0, 500, 10);
        addSpin(posGroup, text('Lề phải Cụm widget (px)', 'Widget group right margin (px)'), 'stack-gap-x', 0, 500, 10);
        addSpin(posGroup, text('Lề trên Cụm widget (px)', 'Widget group top margin (px)'), 'stack-gap-y', 0, 500, 10);

        const individualPositionGroup = new Adw.PreferencesGroup({
            title: text('Vị trí từng tiện ích', 'Individual widget positions'),
            description: text(
                'Đặt tọa độ X và Y cho từng tiện ích. X của đồng hồ tính từ trái; X của các thẻ khác tính từ phải. Y tính từ trên màn hình.',
                'Set X and Y for each widget. The clock X is measured from the left; other cards from the right. Y is measured from the top.'
            ),
        });
        page.add(individualPositionGroup);

        addSpin(individualPositionGroup, text('Đồng hồ - khoảng cách X từ trái (px)', 'Clock - left X margin (px)'), 'widget-clock-x', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Đồng hồ - khoảng cách Y từ trên (px)', 'Clock - top Y margin (px)'), 'widget-clock-y', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Thời tiết - khoảng cách X từ phải (px)', 'Weather - right X margin (px)'), 'widget-weather-x', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Thời tiết - khoảng cách Y từ trên (px)', 'Weather - top Y margin (px)'), 'widget-weather-y', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Hệ thống - khoảng cách X từ phải (px)', 'System - right X margin (px)'), 'widget-system-x', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Hệ thống - khoảng cách Y từ trên (px)', 'System - top Y margin (px)'), 'widget-system-y', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Lịch âm - khoảng cách X từ phải (px)', 'Lunar calendar - right X margin (px)'), 'widget-lunar-x', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Lịch âm - khoảng cách Y từ trên (px)', 'Lunar calendar - top Y margin (px)'), 'widget-lunar-y', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Nhắc nghỉ - khoảng cách X từ phải (px)', 'Break reminder - right X margin (px)'), 'widget-rest-x', 0, 5000, 10);
        addSpin(individualPositionGroup, text('Nhắc nghỉ - khoảng cách Y từ trên (px)', 'Break reminder - top Y margin (px)'), 'widget-rest-y', 0, 5000, 10);

        const updatePositionGroups = () => {
            const individual = settings.get_string('position-mode') === 'individual';
            posGroup.visible = !individual;
            individualPositionGroup.visible = individual;
        };
        modeRow.connect('notify::selected', () => {
            settings.set_string('position-mode', modeRow.selected === 1 ? 'individual' : 'group');
            updatePositionGroups();
        });
        settings.connect('changed::position-mode', () => {
            modeRow.selected = settings.get_string('position-mode') === 'individual' ? 1 : 0;
            updatePositionGroups();
        });
        updatePositionGroups();
    }
}
