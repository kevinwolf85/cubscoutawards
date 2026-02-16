#!/usr/bin/env python3
"""
Fill Cub Scout award certificates from a CSV and output a multi-page PDF.

Usage:
  python3 fill_cub_scout_certs.py \
    --csv "/path/to/Award Sheet - cub_scout_award_template.csv" \
    --output "/path/to/filled.pdf"
"""

from __future__ import annotations

import argparse
import csv
import io
import math
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


DEFAULT_TEMPLATE = str(
    Path(__file__).resolve().parents[1] / "assets" / "templates" / "cub_scout_award_certificate.pdf"
)
FIELDS_PER_PAGE = 8


def _field_name(base: str, index: int) -> str:
    if index == 1:
        return base
    return f"{base}_{index}"


def _build_page_field_map(rows: list[dict[str, str]]) -> dict[str, str]:
    field_map: dict[str, str] = {}
    for i, row in enumerate(rows, start=1):
        field_map[f"name {i}"] = row.get("Scout Name", "").strip()
        field_map[_field_name("On", i)] = _format_date(row.get("Date", ""))
        field_map[_field_name("Cub Scout Pack", i)] = row.get("Pack Number", "").strip()
        field_map[_field_name("for completing", i)] = row.get("Award Name", "").strip()
        field_map[_field_name("Den Leader", i)] = row.get("Den Leader", "").strip()
        field_map[_field_name("Cubmaster", i)] = row.get("Cubmaster", "").strip()
    return field_map


def _format_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
    return value


def _chunk_rows(rows: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        rows = [row for row in reader if any(v.strip() for v in row.values() if v)]
    return rows


def _extract_field_positions(template_reader: PdfReader) -> dict[str, dict[str, object]]:
    page = template_reader.pages[0]
    annots_ref = page.get("/Annots")
    if annots_ref is None:
        raise ValueError("Template PDF has no annotations.")
    annots = annots_ref.get_object()
    fields: dict[str, dict[str, object]] = {}
    for annot_ref in annots:
        annot = annot_ref.get_object()
        name = annot.get("/T")
        if not name:
            continue
        rect = annot.get("/Rect")
        if not rect or len(rect) != 4:
            continue
        mk = annot.get("/MK")
        rotation = 0
        if mk and mk.get("/R") is not None:
            rotation = int(mk.get("/R"))
        fields[str(name)] = {"rect": rect, "rotation": rotation}
    return fields


def _fit_font_size(
    text: str,
    max_width: float,
    font_name: str,
    base_size: float,
    min_size: float = 6.0,
    max_size: float = 12.0,
) -> float:
    size = min(max_size, base_size)
    while size > min_size and canvas.Canvas(io.BytesIO()).stringWidth(
        text, font_name, size
    ) > max_width:
        size -= 0.5
    return max(size, min_size)


def _draw_text(
    c: canvas.Canvas,
    rect: list,
    rotation: int,
    text: str,
    font_name: str,
    base_size: float,
    align: str,
    shift_x: float,
) -> None:
    if not text:
        return
    x1, y1, x2, y2 = [float(v) for v in rect]
    x1 += shift_x
    x2 += shift_x
    width = x2 - x1
    height = y2 - y1
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    draw_width = width if rotation in (0, 180) else height
    font_size = _fit_font_size(text, max(draw_width - 2, 1), font_name, base_size)
    text_width = c.stringWidth(text, font_name, font_size)

    c.saveState()
    c.translate(cx, cy)
    if rotation:
        c.rotate(rotation)
    c.setFont(font_name, font_size)
    y = -font_size / 2.0
    if align == "center":
        c.drawCentredString(0, y, text)
    else:
        x = -draw_width / 2.0 + 1.5
        c.drawString(x, y, text)
    c.restoreState()


def _render_overlay(
    page_size: tuple[float, float],
    field_positions: dict[str, dict[str, object]],
    field_values: dict[str, str],
    font_name: str,
    script_font_name: str | None,
    base_font_size: float,
    shift_x: float,
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page_size)
    for field_name, value in field_values.items():
        info = field_positions.get(field_name)
        if not info:
            continue
        use_font = font_name
        if script_font_name and field_name.startswith(("Den Leader", "Cubmaster")):
            use_font = script_font_name
        align = "center"
        _draw_text(
            c,
            info["rect"],
            int(info["rotation"]),
            value,
            use_font,
            base_font_size,
            align,
            shift_x,
        )
    c.showPage()
    c.save()
    return buffer.getvalue()


def _map_display_shift_to_page(rotate: int, dx_display: float, dy_display: float) -> tuple[float, float]:
    rotate = rotate % 360
    if rotate == 0:
        return dx_display, dy_display
    if rotate == 90:
        return -dy_display, dx_display
    if rotate == 180:
        return -dx_display, -dy_display
    if rotate == 270:
        return dy_display, -dx_display
    return dx_display, dy_display


def fill_certificates(
    csv_path: Path,
    output_path: Path,
    template_path: Path,
    shift_left_inch: float,
    shift_down_inch: float,
    font_name: str,
    script_font_name: str | None,
    font_size: float,
    font_file: str | None = None,
    script_font_file: str | None = None,
) -> None:
    if not template_path.exists():
        raise FileNotFoundError(f"Template PDF not found: {template_path}")

    rows = _read_rows(csv_path)
    if not rows:
        raise ValueError("CSV has no data rows.")

    if font_file and Path(font_file).exists():
        pdfmetrics.registerFont(TTFont(font_name, font_file))
    if script_font_name and script_font_file and Path(script_font_file).exists():
        pdfmetrics.registerFont(TTFont(script_font_name, script_font_file))

    template_reader = PdfReader(str(template_path))
    field_positions = _extract_field_positions(template_reader)
    writer = PdfWriter()

    dx_display = -72.0 * shift_left_inch
    dy_display = -72.0 * shift_down_inch

    page_count = int(math.ceil(len(rows) / FIELDS_PER_PAGE))
    row_chunks = _chunk_rows(rows, FIELDS_PER_PAGE)

    for page_index in range(page_count):
        page_reader = PdfReader(str(template_path))
        page = page_reader.pages[0]

        page_rows = row_chunks[page_index]
        field_map = _build_page_field_map(page_rows)

        page_size = (
            float(page.mediabox.width),
            float(page.mediabox.height),
        )
        overlay_pdf = _render_overlay(
            page_size,
            field_positions,
            field_map,
            font_name,
            script_font_name,
            font_size,
            0.0,
        )
        overlay_page = PdfReader(io.BytesIO(overlay_pdf)).pages[0]
        page.merge_page(overlay_page)

        rotate = page.get("/Rotate") or 0
        tx, ty = _map_display_shift_to_page(rotate, dx_display, dy_display)
        if tx or ty:
            page.add_transformation(Transformation().translate(tx=tx, ty=ty))
        writer.add_page(page)


    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill Cub Scout award certificates from CSV.")
    parser.add_argument("--csv", required=True, help="Path to CSV with headers.")
    parser.add_argument("--output", required=True, help="Output PDF path.")
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        help=f"Template PDF path. Default: {DEFAULT_TEMPLATE}",
    )
    parser.add_argument(
        "--shift-left-inch",
        type=float,
        default=0.5,
        help="Shift output left in display space by this many inches.",
    )
    parser.add_argument(
        "--shift-down-inch",
        type=float,
        default=0.0,
        help="Shift output down in display space by this many inches.",
    )
    parser.add_argument(
        "--font-size",
        type=float,
        default=9.0,
        help="Base font size for filled text.",
    )
    parser.add_argument(
        "--font-name",
        default="Helvetica",
        help="Font name for filled text.",
    )
    parser.add_argument(
        "--script-font-file",
        default="/System/Library/Fonts/Supplemental/Apple Chancery.ttf",
        help="Path to a cursive/script TTF for Den Leader and Cubmaster.",
    )
    parser.add_argument(
        "--script-font-name",
        default="AppleChancery",
        help="Registered font name for the script font.",
    )
    args = parser.parse_args()

    script_font_name = None
    script_font_path = Path(args.script_font_file)
    if script_font_path.exists():
        script_font_name = args.script_font_name

    fill_certificates(
        csv_path=Path(args.csv),
        output_path=Path(args.output),
        template_path=Path(args.template),
        shift_left_inch=args.shift_left_inch,
        shift_down_inch=args.shift_down_inch,
        font_name=args.font_name,
        script_font_name=script_font_name,
        font_size=args.font_size,
        script_font_file=str(script_font_path) if script_font_name else None,
    )


if __name__ == "__main__":
    main()
