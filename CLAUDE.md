# Guess Who Card Generator — Claude Context

## Project Overview

A single-file Python script (`generate.py`) that generates printable Guess Who card PDFs from a folder of images. Uses ReportLab for PDF generation and Pillow for image handling.

## Key Files

- `generate.py` — all logic: config, font management, PDF drawing, CLI
- `example.config` — YAML config with all available settings and their current defaults
- `fonts/` — auto-created directory where font files are cached after first download

## Architecture

- **Config** is defined in `DEFAULT_CONFIG` (dict) and `DEFAULT_CONFIG_YAML` (string). Both must be kept in sync when defaults change.
- **Font registration** happens via `register_font(font_name)`, called at the top of `generate_pdf()`. Built-in ReportLab fonts (Helvetica, Times, etc.) are skipped. For any other font, it looks for `fonts/{font_name}.ttf` locally, and if not found, derives a Google Fonts family name by splitting the CamelCase font name (e.g. `BodoniModa-Bold` → `"Bodoni Moda"`) and downloads the TTF, caching it to `fonts/`.
- **Drawing** is done in `draw_card()`. Card coordinate origin is bottom-left (ReportLab convention).
- **Image sizing**: images always fill the full available height and are center-cropped horizontally via a clip path. Portrait images show narrow; landscape images are clipped.

## Common Tasks

- **Change a default value**: update both `DEFAULT_CONFIG` dict and `DEFAULT_CONFIG_YAML` string, then sync `example.config`.
- **Change card dimensions**: `card.width` / `card.height` in inches.
- **Change font**: update `name_label.font`. Built-in ReportLab fonts (`Helvetica`, `Helvetica-Bold`, `Times-Roman`, etc.) work with no extra steps. For a Google Font, use its CamelCase family name (e.g. `PlayfairDisplay`) — it will be downloaded automatically on first run. To use a font that can't be derived from its name alone, manually place the TTF at `fonts/{font_name}.ttf`.
- **Add a new config key**: add to `DEFAULT_CONFIG`, `DEFAULT_CONFIG_YAML`, `example.config`, and read it in the relevant drawing function using `.get()` with a fallback for backwards compatibility.

## Dependencies

```
reportlab
pillow
pyyaml
```

## Notes

- Colors throughout are RGB lists with values 0.0–1.0.
- All dimensions in config are in inches; multiply by `inch` (from `reportlab.lib.units`) before use in drawing code.
- The `--generate-config` CLI flag writes `DEFAULT_CONFIG_YAML` to a file — it does not reflect runtime state.
