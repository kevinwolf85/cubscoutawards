#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

CARDS_PER_PAGE = 8
CARD_ANCHOR_X = 52.6
CARD_X_STEP = 180.0
CARD_ANCHORS = [
    (CARD_ANCHOR_X + CARD_X_STEP * col, 360.0) for col in range(4)
] + [
    (CARD_ANCHOR_X + CARD_X_STEP * col, 90.0) for col in range(4)
]

# Coordinates are tuned against 34220(15)FillTempl-WOLF.pdf (landscape sheet of 8 cards)
FIELD_LAYOUT = {
    "den_number": {"x": 58.0, "y": 46.0, "size": 7.5, "max_width": 46.0},
    "pack_number": {"x": 66.0, "y": 58.0, "size": 7.5, "max_width": 50.0},
    "date": {"x": 76.0, "y": 72.0, "size": 7.0, "max_width": 84.0},
    "name": {"x": 124.0, "y": -2.0, "size": 10.5, "max_width": 105.0, "max_size": 16.0},
    "den_leader": {"x": 72.0, "y": 24.0, "size": 8.0, "max_width": 106.0, "max_size": 7.5},
    "cubmaster": {"x": 89.0, "y": 10.0, "size": 8.0, "max_width": 106.0, "max_size": 7.5},
}


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        return [row for row in reader if any((v or "").strip() for v in row.values())]


def _chunk_rows(rows: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def _format_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).strftime("%m/%d/%Y")
        except ValueError:
            continue
    return value


def _fit_font_size(c: canvas.Canvas, text: str, font_name: str, base_size: float, max_width: float) -> float:
    if not text:
        return base_size
    size = base_size
    while size > 6.0 and c.stringWidth(text, font_name, size) > max_width:
        size -= 0.4
    return max(size, 6.0)


def _draw_rotated_text(
    c: canvas.Canvas,
    anchor_x: float,
    anchor_y: float,
    text: str,
    font_name: str,
    base_size: float,
    max_width: float,
    field_x: float,
    field_y: float,
    max_size: float | None = None,
) -> None:
    if not text:
        return
    if max_size is not None:
        base_size = min(base_size, max_size)
    size = _fit_font_size(c, text, font_name, base_size, max_width)
    c.saveState()
    c.translate(anchor_x + (field_x - CARD_ANCHOR_X), anchor_y + field_y)
    c.rotate(90)
    c.setFont(font_name, size)
    c.drawString(0, 0, text)
    c.restoreState()


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


def fill_rank_cards(
    csv_path: Path,
    output_path: Path,
    template_path: Path,
    shift_left_inch: float,
    shift_down_inch: float,
    font_name: str,
    script_font_name: str | None,
    font_size: float,
    script_font_size: float | None = None,
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

    signature_font = script_font_name or font_name
    signature_size = script_font_size if script_font_size is not None else max(font_size - 1.0, 7.0)

    dx_display = -72.0 * shift_left_inch
    dy_display = -72.0 * shift_down_inch

    writer = PdfWriter()
    chunks = _chunk_rows(rows, CARDS_PER_PAGE)
    for chunk in chunks:
        page = PdfReader(str(template_path)).pages[0]
        page_size = (float(page.mediabox.width), float(page.mediabox.height))

        overlay_buffer = io.BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=page_size)

        for idx, row in enumerate(chunk):
            anchor_x, anchor_y = CARD_ANCHORS[idx]
            den_number = (row.get("Den Number") or row.get("Den No.") or "").strip()
            pack_number = (row.get("Pack Number") or "").strip()
            date_value = _format_date(row.get("Date") or "")
            scout_name = (row.get("Scout Name") or "").strip()
            den_leader = (row.get("Den Leader") or "").strip()
            cubmaster = (row.get("Cubmaster") or "").strip()

            _draw_rotated_text(
                c,
                anchor_x,
                anchor_y,
                den_number,
                font_name,
                FIELD_LAYOUT["den_number"]["size"],
                FIELD_LAYOUT["den_number"]["max_width"],
                FIELD_LAYOUT["den_number"]["x"],
                FIELD_LAYOUT["den_number"]["y"],
            )
            _draw_rotated_text(
                c,
                anchor_x,
                anchor_y,
                pack_number,
                font_name,
                FIELD_LAYOUT["pack_number"]["size"],
                FIELD_LAYOUT["pack_number"]["max_width"],
                FIELD_LAYOUT["pack_number"]["x"],
                FIELD_LAYOUT["pack_number"]["y"],
            )
            _draw_rotated_text(
                c,
                anchor_x,
                anchor_y,
                date_value,
                font_name,
                FIELD_LAYOUT["date"]["size"],
                FIELD_LAYOUT["date"]["max_width"],
                FIELD_LAYOUT["date"]["x"],
                FIELD_LAYOUT["date"]["y"],
            )
            _draw_rotated_text(
                c,
                anchor_x,
                anchor_y,
                scout_name,
                font_name,
                max(FIELD_LAYOUT["name"]["size"], font_size),
                FIELD_LAYOUT["name"]["max_width"],
                FIELD_LAYOUT["name"]["x"],
                FIELD_LAYOUT["name"]["y"],
                FIELD_LAYOUT["name"].get("max_size"),
            )
            _draw_rotated_text(
                c,
                anchor_x,
                anchor_y,
                den_leader,
                signature_font,
                max(FIELD_LAYOUT["den_leader"]["size"], signature_size),
                FIELD_LAYOUT["den_leader"]["max_width"],
                FIELD_LAYOUT["den_leader"]["x"],
                FIELD_LAYOUT["den_leader"]["y"],
                FIELD_LAYOUT["den_leader"].get("max_size"),
            )
            _draw_rotated_text(
                c,
                anchor_x,
                anchor_y,
                cubmaster,
                signature_font,
                max(FIELD_LAYOUT["cubmaster"]["size"], signature_size),
                FIELD_LAYOUT["cubmaster"]["max_width"],
                FIELD_LAYOUT["cubmaster"]["x"],
                FIELD_LAYOUT["cubmaster"]["y"],
                FIELD_LAYOUT["cubmaster"].get("max_size"),
            )

        c.showPage()
        c.save()
        overlay_pdf = PdfReader(io.BytesIO(overlay_buffer.getvalue())).pages[0]
        page.merge_page(overlay_pdf)

        rotate = page.get("/Rotate") or 0
        tx, ty = _map_display_shift_to_page(rotate, dx_display, dy_display)
        if tx or ty:
            page.add_transformation(Transformation().translate(tx=tx, ty=ty))

        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)
