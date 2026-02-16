#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_file

# Import the generator script
import sys

UI_DIR = Path(__file__).resolve().parent
REPO_ROOT = UI_DIR.parent.parent
DEV_DIR = REPO_ROOT / "dev"
DEFAULT_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "cub_scout_award_certificate.pdf"
TEMPLATE_PATH = Path(os.environ.get("CERT_TEMPLATE_PATH", str(DEFAULT_TEMPLATE_PATH))).expanduser()

if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from fill_cub_scout_certs import fill_certificates  # noqa: E402

app = Flask(__name__, static_folder=str(UI_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB CSV upload limit

SCRIPT_FONTS = {
    "AppleChancery": [
        "/System/Library/Fonts/Supplemental/Apple Chancery.ttf",
    ],
    "BradleyHand": [
        "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
    ],
    "BrushScript": [
        "/System/Library/Fonts/Supplemental/Brush Script.ttf",
    ],
    "Georgia": [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ],
    "Verdana": [
        "/System/Library/Fonts/Supplemental/Verdana.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "Tahoma": [
        "/System/Library/Fonts/Supplemental/Tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "TrebuchetMS": [
        "/System/Library/Fonts/Supplemental/Trebuchet MS.ttf",
    ],
    "TimesNewRoman": [
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ],
    "CourierNew": [
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
    "Geneva": [
        "/System/Library/Fonts/Supplemental/Geneva.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "Chalkduster": [
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
    ],
}


def _resolve_script_font_file(name: str) -> Optional[str]:
    paths = SCRIPT_FONTS.get(name)
    if not paths:
        return None
    for path in paths:
        if Path(path).exists():
            return path
    return None


def _safe_output_name(value: str) -> str:
    filename = Path(value or "").name
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    if not filename:
        filename = "filled_awards.pdf"
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"
    return filename


def _parse_float(raw_value: str, fallback: float) -> float:
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return fallback


@app.post("/generate")
def generate_pdf():
    if "csv" not in request.files:
        return jsonify({"error": "CSV file missing"}), 400

    csv_file = request.files["csv"]
    if not csv_file.filename:
        return jsonify({"error": "CSV file missing"}), 400

    font_name = request.form.get("fontName", "Helvetica")
    script_font = request.form.get("scriptFont", "AppleChancery")
    shift_left = _parse_float(request.form.get("shiftLeft", "0.5"), fallback=0.5)
    shift_down = _parse_float(request.form.get("shiftDown", "0.0"), fallback=0.0)
    font_size = _parse_float(request.form.get("fontSize", "9"), fallback=9.0)
    output_name = _safe_output_name(request.form.get("outputName", "filled_awards.pdf"))

    if not TEMPLATE_PATH.exists():
        return jsonify({"error": "Template PDF not configured on server."}), 500

    script_font_file = None
    if script_font and script_font != "None":
        script_font_file = _resolve_script_font_file(script_font)
    font_file = _resolve_script_font_file(font_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        csv_path = tmpdir_path / "input.csv"
        out_path = tmpdir_path / output_name
        csv_file.save(csv_path)

        fill_certificates(
            csv_path=csv_path,
            output_path=out_path,
            template_path=TEMPLATE_PATH,
            shift_left_inch=shift_left,
            shift_down_inch=shift_down,
            font_name=font_name,
            script_font_name=script_font if script_font_file else None,
            font_size=font_size,
            font_file=font_file,
            script_font_file=script_font_file,
        )

        return send_file(
            out_path,
            as_attachment=True,
            download_name=output_name,
            mimetype="application/pdf",
        )




@app.get("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5178")), debug=False)
