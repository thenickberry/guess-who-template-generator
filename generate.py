#!/usr/bin/env python3
"""
Guess Who Card Generator
========================
Generates a printable PDF of custom Guess Who cards from a folder of images.

Usage:
    python guess_who_cards.py /path/to/images
    python guess_who_cards.py /path/to/images --config my_config.yaml
    python guess_who_cards.py --generate-config              # dump default config

Card specs (defaults, all configurable via YAML):
    - Card size: 1.25" x 1.375" (matches official Guess Who)
    - Paper size: 8.5" x 11" (US Letter)
    - Grid: 5 columns x 5 rows per page
    - Thin white border around each card
    - Character name derived from image filename (minus extension)
    - Crop marks for cutting guides
"""

import argparse
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

import yaml
from reportlab.lib.units import inch
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageEnhance, ImageOps


# ──────────────────────────────────────────────
# Font management
# ──────────────────────────────────────────────

FONTS_DIR = Path(__file__).parent / "fonts"

# Built-in ReportLab fonts that require no registration
BUILTIN_FONTS = {
    "Courier", "Courier-Bold", "Courier-BoldOblique", "Courier-Oblique",
    "Helvetica", "Helvetica-Bold", "Helvetica-BoldOblique", "Helvetica-Oblique",
    "Symbol",
    "Times-Bold", "Times-BoldItalic", "Times-Italic", "Times-Roman",
    "ZapfDingbats",
}


def _camel_to_words(name: str) -> str:
    """Convert a CamelCase font name to spaced words for Google Fonts lookup.

    e.g. "BodoniModa" -> "Bodoni Moda", "PlayfairDisplay" -> "Playfair Display"
    Strips any style suffix (e.g. "-Bold", "-Italic") before converting.
    """
    base = name.split("-")[0]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base)


def _google_fonts_ttf_url(family: str) -> str:
    """Return the first TTF download URL for a Google Fonts family."""
    api_url = f"https://fonts.googleapis.com/css2?family={urllib.parse.quote(family)}"
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": "Mozilla/4.0"},  # legacy UA returns TTF format
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        css = resp.read().decode("utf-8")
    urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)
    if not urls:
        raise RuntimeError(f"No TTF URLs found in Google Fonts response for '{family}'.")
    return urls[0]


def register_font(font_name: str) -> None:
    """Register a font with ReportLab if it isn't a built-in.

    Looks for fonts/{font_name}.ttf locally. If not found, attempts to
    download it from Google Fonts using a family name derived from font_name.
    Downloaded files are cached in fonts/ for subsequent runs.
    """
    if font_name in BUILTIN_FONTS:
        return

    FONTS_DIR.mkdir(exist_ok=True)
    font_path = FONTS_DIR / f"{font_name}.ttf"

    if not font_path.exists():
        family = _camel_to_words(font_name)
        print(f"Font '{font_name}' not found locally. Downloading '{family}' from Google Fonts...")
        try:
            url = _google_fonts_ttf_url(family)
            urllib.request.urlretrieve(url, font_path)
            print(f"  Saved: {font_path}")
        except Exception as e:
            raise RuntimeError(
                f"Could not download font '{font_name}': {e}\n"
                f"Manually place '{font_name}.ttf' in '{FONTS_DIR}'."
            ) from e

    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))


# ──────────────────────────────────────────────
# Image enhancement
# ──────────────────────────────────────────────

def enhance_image(img: Image.Image, cfg: dict) -> Image.Image:
    ec = cfg.get("image_enhance", {})
    alpha = img.split()[3] if img.mode == "RGBA" else None
    img = img.convert("RGB")
    if ec.get("auto_contrast", True):
        img = ImageOps.autocontrast(img)
    for attr, key, default in [
        (ImageEnhance.Color,      "saturation", 1.3),
        (ImageEnhance.Contrast,   "contrast",   1.1),
        (ImageEnhance.Brightness, "brightness", 1.0),
        (ImageEnhance.Sharpness,  "sharpness",  1.0),
    ]:
        factor = ec.get(key, default)
        if factor != 1.0:
            img = attr(img).enhance(factor)
    if alpha:
        img = img.convert("RGBA")
        img.putalpha(alpha)
    return img


# ──────────────────────────────────────────────
# Default configuration (embedded)
# ──────────────────────────────────────────────

DEFAULT_CONFIG = {
    "page": {
        "width": 8.5,
        "height": 11.0,
        "margin_x": 0.5,
        "margin_y": 0.5,
    },
    "card": {
        "width": 1.25,
        "height": 1.375,
        "columns": 5,
        "rows": 5,
        "padding": 0.125,
        "background_color": [1.0, 1.0, 1.0],
    },
    "image": {
        "padding": 0.0,
    },
    "name_label": {
        "height": 0.28,
        "font": "Helvetica-Bold",
        "font_size": 12,
        "color": [0.0, 0.0, 0.0],
        "outline_color": [1.0, 1.0, 1.0],
        "outline_width": 2.0,
        "bottom_padding": 0.15,
    },
    "border": {
        "color": [1.0, 1.0, 1.0],
        "width": 0,
    },
    "crop_marks": {
        "enabled": True,
        "length": 0.15,
        "offset": 0.04,
        "color": [0.4, 0.4, 0.4],
        "width": 0.5,
    },
    "game": {
        "max_cards": 24,
        "sets": 2,
    },
    "duplex": {
        "back_offset_x": 0.0,
        "back_offset_y": 0.0,
    },
    "card_back": {
        "set_colors": [[0.18, 0.38, 0.72], [0.72, 0.18, 0.18]],
        "frame_color": [1.0, 1.0, 1.0],
        "frame_width": 1.5,
        "frame_margin": 0.07,
        "qm_color": [1.0, 1.0, 1.0],
        "qm_alpha": 0.30,
    },
    "image_extensions": [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"],
    "image_enhance": {
        "auto_contrast": True,
        "saturation": 1.3,
        "contrast": 1.1,
        "brightness": 1.0,
        "sharpness": 1.0,
    },
}

# Nicely formatted YAML template for --generate-config
DEFAULT_CONFIG_YAML = """\
# ============================================================
# Guess Who Card Generator — Configuration
# ============================================================
# All dimensions are in inches unless noted otherwise.
# Colors use RGB values from 0.0 to 1.0.
# ============================================================

# --- Page setup ---
page:
  width: 8.5
  height: 11.0
  margin_x: 0.5
  margin_y: 0.5

# --- Card dimensions ---
card:
  width: 1.5
  height: 1.375
  columns: 5
  rows: 5
  padding: 0.125                           # spacing around each card in the grid
  background_color: [1.0, 1.0, 1.0]   # white

# --- Image area ---
image:
  padding: 0.06                            # padding inside card around the image

# --- Name label ---
name_label:
  height: 0.28
  font: "Helvetica-Bold"
  font_size: 8                            # points
  color: [0.0, 0.0, 0.0]                  # black
  outline_color: [1.0, 1.0, 1.0]          # white outline around letters
  outline_width: 2.0                      # outline stroke width in points (0 to disable)
  bottom_padding: 0.15                    # gap between card bottom and text baseline

# --- Card border ---
border:
  color: [1.0, 1.0, 1.0]                  # white
  width: 0                                # points (0 to disable)

# --- Crop marks (cutting guides) ---
crop_marks:
  enabled: true
  length: 0.15
  offset: 0.04                            # gap between card edge and mark
  color: [0.4, 0.4, 0.4]                  # medium gray
  width: 0.5                              # points

# --- Duplex alignment ---
# If front and back are misaligned when printed, adjust these to compensate.
# Positive x shifts backs to the right; positive y shifts backs up.
# Tip: print one page, hold it to light against its back, measure the offset,
# then set back_offset_x / back_offset_y to the opposite of what you measure.
duplex:
  back_offset_x: 0.0              # inches, horizontal shift for back pages
  back_offset_y: 0.0              # inches, vertical shift for back pages

# --- Game settings ---
game:
  max_cards: 24                           # standard Guess Who character count
  sets: 2                                 # number of identical sets to produce

# --- Card back ---
card_back:
  set_colors:                              # one color per set (RGB)
    - [0.18, 0.38, 0.72]                  # set 1: blue
    - [0.72, 0.18, 0.18]                  # set 2: red
  frame_color: [1.0, 1.0, 1.0]            # white
  frame_width: 1.5                         # points
  frame_margin: 0.07                       # inches from card edge to frame
  qm_color: [1.0, 1.0, 1.0]              # question mark color
  qm_alpha: 0.30                           # question mark opacity (0.0–1.0)

# --- Supported image formats ---
image_extensions:
  - .png
  - .jpg
  - .jpeg
  - .bmp
  - .gif
  - .tiff
  - .webp

# --- Image enhancement ---
image_enhance:
  auto_contrast: true          # normalize tonal range
  saturation: 1.3              # color boost (1.0 = none)
  contrast: 1.1                # contrast boost (1.0 = none)
  brightness: 1.0              # brightness (1.0 = none)
  sharpness: 1.0               # sharpness (1.0 = none)
"""


# ──────────────────────────────────────────────
# Config loading
# ──────────────────────────────────────────────

def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override values win."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: Optional[str]) -> dict:
    """Load config from YAML file, merged on top of defaults."""
    cfg = DEFAULT_CONFIG.copy()
    if config_path:
        path = Path(config_path)
        if not path.is_file():
            print(f"Error: Config file '{config_path}' not found.")
            sys.exit(1)
        with open(path) as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = deep_merge(cfg, user_cfg)
        print(f"Loaded config from: {config_path}")
    else:
        print("Using default configuration.")
    return cfg


def color_from_list(rgb: list) -> Color:
    """Convert an [r, g, b] list (0-1 range) to a reportlab Color."""
    return Color(rgb[0], rgb[1], rgb[2])


# ──────────────────────────────────────────────
# Drawing functions
# ──────────────────────────────────────────────

def get_grid_origin(cfg):
    """Calculate top-left origin so the card grid is centered on the page."""
    card_w = cfg["card"]["width"] * inch
    card_h = cfg["card"]["height"] * inch
    pad = cfg["card"].get("padding", 0.0) * inch
    page_w = cfg["page"]["width"] * inch
    page_h = cfg["page"]["height"] * inch
    cols = cfg["card"]["columns"]
    rows = cfg["card"]["rows"]

    cell_w = card_w + 2 * pad
    cell_h = card_h + 2 * pad
    grid_width = cols * cell_w
    grid_height = rows * cell_h
    origin_x = (page_w - grid_width) / 2
    origin_y = page_h - (page_h - grid_height) / 2
    return origin_x, origin_y


def draw_crop_marks(c, x, y, w, h, cfg):
    """Draw crop marks at the four corners of a card rectangle."""
    cm = cfg["crop_marks"]
    if not cm["enabled"]:
        return

    c.setStrokeColor(color_from_list(cm["color"]))
    c.setLineWidth(cm["width"])

    offset = cm["offset"] * inch
    length = cm["length"] * inch

    corners = [
        (x, y + h, -1, 1),
        (x + w, y + h, 1, 1),
        (x, y, -1, -1),
        (x + w, y, 1, -1),
    ]
    for cx, cy, hdx, vdy in corners:
        c.line(cx + hdx * offset, cy, cx + hdx * (offset + length), cy)
        c.line(cx, cy + vdy * offset, cx, cy + vdy * (offset + length))


def draw_card(c, x, y, image_path, name, cfg):
    """Draw a single Guess Who card at (x, y) bottom-left."""
    card_w = cfg["card"]["width"] * inch
    card_h = cfg["card"]["height"] * inch
    img_pad = cfg["image"]["padding"] * inch
    label_h = cfg["name_label"]["height"] * inch
    label_font = cfg["name_label"]["font"]
    label_size = cfg["name_label"]["font_size"]
    label_color = color_from_list(cfg["name_label"]["color"])
    label_bottom_pad = cfg["name_label"].get("bottom_padding", 0.2) * inch

    # Card background
    c.setFillColor(color_from_list(cfg["card"]["background_color"]))
    c.rect(x, y, card_w, card_h, fill=1, stroke=0)

    # --- Image area (full card) ---
    img_x = x
    img_y = y
    img_max_w = card_w
    img_max_h = card_h

    try:
        pil_img = enhance_image(Image.open(image_path), cfg)
        pil_w, pil_h = pil_img.size
        aspect = pil_w / pil_h

        # Cover fill: scale so image fills the full card in both dimensions, clipping overflow
        scale = max(img_max_w / pil_w, img_max_h / pil_h)
        draw_w = pil_w * scale
        draw_h = pil_h * scale
        draw_x = img_x + (img_max_w - draw_w) / 2
        draw_y = img_y + (img_max_h - draw_h) / 2

        c.saveState()
        clip = c.beginPath()
        clip.rect(img_x, img_y, img_max_w, img_max_h)
        c.clipPath(clip, stroke=0, fill=0)
        c.drawImage(ImageReader(pil_img), draw_x, draw_y, draw_w, draw_h,
                    preserveAspectRatio=False, mask='auto')
        c.restoreState()
    except Exception as e:
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.rect(img_x, img_y, img_max_w, img_max_h, fill=1, stroke=0)
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica", 6)
        c.drawCentredString(x + card_w / 2, y + card_h / 2, "Image Error")
        print(f"  Warning: Could not load image: {image_path} ({e})")

    # --- Name label ---
    label_outline_color = color_from_list(cfg["name_label"].get("outline_color", [1.0, 1.0, 1.0]))
    label_outline_width = cfg["name_label"].get("outline_width", 2.0)
    c.setFont(label_font, label_size)
    display_name = name
    max_text_w = card_w - 2 * img_pad
    while c.stringWidth(display_name, label_font, label_size) > max_text_w:
        display_name = display_name[:-1]
        if len(display_name) <= 1:
            break
    label_y = y + label_bottom_pad + (label_size / 3)
    label_x = x + card_w / 2 - c.stringWidth(display_name, label_font, label_size) / 2

    # Outline pass (stroke only)
    c.saveState()
    c.setStrokeColor(label_outline_color)
    c.setLineWidth(label_outline_width)
    t = c.beginText(label_x, label_y)
    t.setTextRenderMode(1)  # stroke only
    t.setFont(label_font, label_size)
    t.textLine(display_name)
    c.drawText(t)
    c.restoreState()

    # Fill pass
    c.setFillColor(label_color)
    c.drawCentredString(x + card_w / 2, label_y, display_name)

    # --- Border ---
    c.setStrokeColor(color_from_list(cfg["border"]["color"]))
    c.setLineWidth(cfg["border"]["width"])
    c.rect(x, y, card_w, card_h, fill=0, stroke=1)

    # --- Crop marks ---
    draw_crop_marks(c, x, y, card_w, card_h, cfg)


# ──────────────────────────────────────────────
# Image collection
# ──────────────────────────────────────────────

def collect_images(image_dir, cfg):
    """Collect and sort image files from the given directory."""
    image_dir = Path(image_dir)
    if not image_dir.is_dir():
        print(f"Error: '{image_dir}' is not a valid directory.")
        sys.exit(1)

    extensions = set(cfg["image_extensions"])
    images = []
    for f in sorted(image_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            name = f.stem.replace("_", " ").replace("-", " ").title()
            images.append((str(f), name))

    if not images:
        print(f"Error: No image files found in '{image_dir}'.")
        print(f"  Supported formats: {', '.join(sorted(extensions))}")
        sys.exit(1)

    return images


def draw_card_back(c, x, y, bg_color, cfg):
    """Draw the back of a Guess Who card at (x, y) bottom-left."""
    card_w = cfg["card"]["width"] * inch
    card_h = cfg["card"]["height"] * inch
    cb = cfg.get("card_back", {})

    frame_color = color_from_list(cb.get("frame_color", [1.0, 1.0, 1.0]))
    frame_width = cb.get("frame_width", 1.5)
    frame_margin = cb.get("frame_margin", 0.07) * inch
    qm_col = cb.get("qm_color", [1.0, 1.0, 1.0])
    qm_alpha = cb.get("qm_alpha", 0.30)
    qm_font = cfg["name_label"]["font"]

    # Background
    c.setFillColor(bg_color)
    c.rect(x, y, card_w, card_h, fill=1, stroke=0)

    # Scattered question marks — clipped to card bounds
    # Each entry: (x_frac, y_frac, angle_degrees, font_size)
    scatter = [
        (0.10, 0.90, 20,  16),
        (0.42, 0.93, -8,  11),
        (0.75, 0.85, 38,  14),
        (0.05, 0.65, -30, 20),
        (0.58, 0.70, 12,  13),
        (0.88, 0.60, -22, 17),
        (0.25, 0.50,  0,  22),
        (0.72, 0.45, -40, 12),
        (0.48, 0.50, 55,  10),
        (0.15, 0.30, 28,  15),
        (0.80, 0.28, -15, 19),
        (0.38, 0.18, -50, 13),
        (0.65, 0.10, 18,  16),
        (0.90, 0.08, -28, 11),
        (0.20, 0.08, 42,  14),
    ]

    c.saveState()
    clip = c.beginPath()
    clip.rect(x, y, card_w, card_h)
    c.clipPath(clip, stroke=0, fill=0)

    c.setFillColor(Color(qm_col[0], qm_col[1], qm_col[2], qm_alpha))
    for xf, yf, angle, size in scatter:
        qx = x + xf * card_w
        qy = y + yf * card_h
        c.saveState()
        c.translate(qx, qy)
        c.rotate(angle)
        c.setFont(qm_font, size)
        c.drawCentredString(0, -size / 3, "?")
        c.restoreState()

    c.restoreState()

    # Outer frame
    c.setStrokeColor(frame_color)
    c.setLineWidth(frame_width)
    c.rect(x + frame_margin, y + frame_margin,
           card_w - 2 * frame_margin, card_h - 2 * frame_margin,
           fill=0, stroke=1)

    # Crop marks
    draw_crop_marks(c, x, y, card_w, card_h, cfg)


# ──────────────────────────────────────────────
# PDF generation
# ──────────────────────────────────────────────

def generate_pdf(images, output_path, cfg):
    """Generate the Guess Who card PDF.

    Page order per set: front page(s) immediately followed by their back page(s),
    so duplex printing (flip on long edge) produces correctly aligned backs.
    Columns on back pages are mirrored so each back aligns with its front card.
    """
    register_font(cfg["name_label"]["font"])

    page_w = cfg["page"]["width"] * inch
    page_h = cfg["page"]["height"] * inch
    card_w = cfg["card"]["width"] * inch
    card_h = cfg["card"]["height"] * inch
    cols = cfg["card"]["columns"]
    rows = cfg["card"]["rows"]
    pad = cfg["card"].get("padding", 0.0) * inch
    cell_w = card_w + 2 * pad
    cell_h = card_h + 2 * pad
    num_sets = cfg["game"].get("sets", 1)
    set_colors = cfg.get("card_back", {}).get(
        "set_colors", [[0.18, 0.38, 0.72], [0.72, 0.18, 0.18]]
    )

    c = canvas.Canvas(output_path, pagesize=(page_w, page_h))
    c.setTitle("Guess Who - Custom Cards")

    origin_x, origin_y = get_grid_origin(cfg)
    cards_per_page = cols * rows

    # Split images into pages once; reuse across sets
    pages = [images[i:i + cards_per_page] for i in range(0, len(images), cards_per_page)]
    total_pdf_pages = len(pages) * num_sets * 2
    print(f"Generating {len(images)} cards × {num_sets} set(s) → {total_pdf_pages} pages...")

    first_page = True
    for set_idx in range(num_sets):
        back_color = color_from_list(set_colors[set_idx % len(set_colors)])
        print(f"\nSet {set_idx + 1}:")

        for page_images in pages:
            # ── Front page ──────────────────────────────────────────────
            if not first_page:
                c.showPage()
            first_page = False

            for page_idx, (img_path, name) in enumerate(page_images):
                col = page_idx % cols
                row = page_idx // cols
                card_x = origin_x + col * cell_w + pad
                card_y = origin_y - (row + 1) * cell_h + pad
                draw_card(c, card_x, card_y, img_path, name, cfg)
                print(f"  [front] {name}")

            # ── Back page (mirror columns for duplex alignment) ──────────
            c.showPage()
            duplex = cfg.get("duplex", {})
            back_offset_x = duplex.get("back_offset_x", 0.0) * inch
            back_offset_y = duplex.get("back_offset_y", 0.0) * inch
            for page_idx in range(len(page_images)):
                col = cols - 1 - (page_idx % cols)
                row = page_idx // cols
                card_x = origin_x + col * cell_w + pad + back_offset_x
                card_y = origin_y - (row + 1) * cell_h + pad + back_offset_y
                draw_card_back(c, card_x, card_y, back_color, cfg)

    c.save()
    print(f"\nDone! Saved to: {output_path}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def generate_default_config(output_path):
    """Write the default config to a YAML file."""
    with open(output_path, "w") as f:
        f.write(DEFAULT_CONFIG_YAML)
    print(f"Default config written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate printable Guess Who cards from a folder of images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
    python guess_who_cards.py ./photos
    python guess_who_cards.py ./photos --config my_config.yaml
    python guess_who_cards.py ./photos --config my_config.yaml --output cards.pdf
    python guess_who_cards.py --generate-config
    python guess_who_cards.py --generate-config custom.yaml

Card names are derived from filenames:
    "anna_smith.png"  →  "Anna Smith"
    "uncle-bob.jpg"   →  "Uncle Bob"
""",
    )
    parser.add_argument("image_dir", nargs="?", help="Path to folder containing character images")
    parser.add_argument("--output", "-o", default="guess_who_cards.pdf",
                        help="Output PDF filename (default: guess_who_cards.pdf)")
    parser.add_argument("--config", "-c", default=None,
                        help="Path to YAML config file (default: built-in defaults)")
    parser.add_argument("--generate-config", metavar="FILE", nargs="?",
                        const="guess_who_config.yaml",
                        help="Generate a default config file and exit (default: guess_who_config.yaml)")
    args = parser.parse_args()

    # Handle --generate-config
    if args.generate_config:
        generate_default_config(args.generate_config)
        sys.exit(0)

    if not args.image_dir:
        parser.error("image_dir is required unless using --generate-config")

    cfg = load_config(args.config)
    max_cards = cfg["game"]["max_cards"]

    images = collect_images(args.image_dir, cfg)
    print(f"Found {len(images)} images in '{args.image_dir}'")

    if len(images) > max_cards:
        print(f"Note: Found {len(images)} images. Using first {max_cards} per config.")
        images = images[:max_cards]
    elif len(images) < max_cards:
        print(f"Note: Only {len(images)} images found. Config expects {max_cards}.")

    generate_pdf(images, args.output, cfg)


if __name__ == "__main__":
    main()

