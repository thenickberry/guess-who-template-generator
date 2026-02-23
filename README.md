# Guess Who Card Generator

Generates a printable PDF of custom Guess Who cards from a folder of images.

## Requirements

**macOS / Linux**
```bash
pip3 install reportlab pillow pyyaml
```

**Windows**
```bash
pip install reportlab pillow pyyaml
```

## Usage

**macOS / Linux**
```bash
# Generate cards from a folder of images
python3 generate.py ./photos

# Use a custom config file
python3 generate.py ./photos --config my_config.yaml

# Specify output filename
python3 generate.py ./photos --output my_cards.pdf

# Write a default config file to customize
python3 generate.py --generate-config my_config.yaml
```

**Windows**
```bash
# Generate cards from a folder of images
python generate.py ./photos

# Use a custom config file
python generate.py ./photos --config my_config.yaml

# Specify output filename
python generate.py ./photos --output my_cards.pdf

# Write a default config file to customize
python generate.py --generate-config my_config.yaml
```

## Card Layout

- **Paper:** 8.5" × 11" (US Letter)
- **Card size:** 1.5" × 1.375"
- **Grid:** 5 columns × 5 rows (25 cards per page)
- **Max cards:** 24 (standard Guess Who character count)
- **Crop marks** included for cutting guides

## Character Names

Names are derived automatically from image filenames:

```
anna_smith.png  →  Anna Smith
uncle-bob.jpg   →  Uncle Bob
```

## Configuration

Copy `example_config` and adjust as needed. All settings are optional — any omitted values fall back to defaults.

| Section | Key | Description |
|---|---|---|
| `page` | `width`, `height` | Page dimensions in inches |
| `page` | `margin_x`, `margin_y` | Page margins in inches |
| `card` | `width`, `height` | Card dimensions in inches |
| `card` | `columns`, `rows` | Grid layout |
| `card` | `background_color` | RGB color `[r, g, b]` (0–1) |
| `image` | `padding` | Padding around the photo inside the card |
| `name_label` | `height` | Height of the name strip at the bottom |
| `name_label` | `font` | ReportLab font name |
| `name_label` | `font_size` | Font size in points |
| `name_label` | `color` | Text color as RGB |
| `name_label` | `bottom_padding` | Gap between card bottom and text baseline |
| `border` | `color` | Border color as RGB |
| `border` | `width` | Border stroke width in points |
| `crop_marks` | `enabled` | Show/hide crop marks |
| `crop_marks` | `length`, `offset` | Mark size and gap in inches |
| `crop_marks` | `color`, `width` | Mark appearance |
| `game` | `max_cards` | Maximum number of cards to generate |
| `image_extensions` | — | List of accepted file extensions |

## Fonts

The default font is `Helvetica-Bold`, which is built into ReportLab and requires no setup.

To use a custom font, set `name_label.font` in your config to the font name:

- **Built-in ReportLab fonts** (`Helvetica`, `Helvetica-Bold`, `Times-Roman`, `Courier`, etc.) — work with no extra steps.
- **Google Fonts** — use the CamelCase family name (e.g. `BodoniModa`, `PlayfairDisplay`). The TTF is downloaded automatically on first run and cached in `fonts/`.
- **Any other TTF** — place the file at `fonts/{FontName}.ttf` and use `FontName` in the config.

Style suffixes like `-Bold` and `-Italic` are stripped when deriving the Google Fonts family name, so `BodoniModa-Bold` looks up `"Bodoni Moda"` and downloads the regular weight TTF. If you need a specific weight, download the TTF manually and place it in `fonts/`.
