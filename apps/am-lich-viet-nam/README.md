# Vietnamese Lunar Calendar

A GTK4/Libadwaita desktop calendar that displays Vietnamese lunar dates alongside the Gregorian calendar, using the MacTahoe dark appearance.

## Features

- Monthly Gregorian calendar with lunar days, leap months, and Can Chi.
- Details for the selected date, including its solar and lunar dates and year/month/day Can Chi.
- Vietnamese holidays and commemorative dates, including Lunar New Year, Hung Kings' Commemoration, Mid-Autumn Festival, and national holidays.
- Navigate months with the mouse or keyboard; use **Today** to return to the current date.
- Works offline.

## Run

```bash
cd "$HOME/mactahoe-ubuntu/apps/am-lich-viet-nam"
python3 amlich_app.py
```

Or launch **Vietnamese Lunar Calendar** from GNOME or run:

```bash
am-lich-viet-nam
```

## Keyboard shortcuts

| Key | Action |
|---|---|
| `←` / `Page Up` | Previous month |
| `→` / `Page Down` | Next month |
| `Home` / `Ctrl+T` | Go to today |

## Files

- `amlich_app.py` — GTK4 interface.
- `lunar.py` — Ho Ngoc Duc solar/lunar conversion algorithm using UTC+7.
- `holidays.py` — Vietnamese holidays and commemorative dates.
- `style.css` — application styling.
- `assets/vn.ihoan.AmLich.svg` — application icon.
- `test_lunar.py` — algorithm and holiday tests.

## Test

```bash
cd "$HOME/mactahoe-ubuntu/apps/am-lich-viet-nam"
python3 -m unittest -v test_lunar.py
```

## Notes

- Uses Vietnam time (UTC+7) and supports dates from 1800 to 2199.
- Leap months are calculated automatically; lunar holidays are not repeated in leap months.
- Can Chi day names use the Julian Day Number; month Can Chi uses the lunar year's stem.
