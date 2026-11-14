import GLib from 'gi://GLib';

export function getLanguage(settings) {
    const preference = settings.get_string('ui-language');
    if (preference === 'vi' || preference === 'en') {
        return preference;
    }

    return GLib.get_language_names().some(name => /^vi([_-]|$)/i.test(name))
        ? 'vi'
        : 'en';
}

export function textFor(language, vietnamese, english) {
    return language === 'vi' ? vietnamese : english;
}
