#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_file

# Import the generator script
import sys

DEV_DIR = Path("/Users/kevinwolf/Library/CloudStorage/OneDrive-SwansonHealthProducts/dev")
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from fill_cub_scout_certs import fill_certificates  # noqa: E402

UI_DIR = Path("/Users/kevinwolf/Library/CloudStorage/OneDrive-SwansonHealthProducts/dev/cert_form_ui")
app = Flask(__name__, static_folder=str(UI_DIR), static_url_path="")

SCRIPT_FONTS = {
    "AppleChancery": "/System/Library/Fonts/Supplemental/Apple Chancery.ttf",
    "BradleyHand": "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
    "BrushScript": "/System/Library/Fonts/Supplemental/Brush Script.ttf",
    "Georgia": "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "Verdana": "/System/Library/Fonts/Supplemental/Verdana.ttf",
    "Tahoma": "/System/Library/Fonts/Supplemental/Tahoma.ttf",
    "TrebuchetMS": "/System/Library/Fonts/Supplemental/Trebuchet MS.ttf",
    "TimesNewRoman": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "CourierNew": "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "Geneva": "/System/Library/Fonts/Supplemental/Geneva.ttf",
    "Chalkduster": "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
}


def _resolve_script_font_file(name: str) -> Optional[str]:
    path = SCRIPT_FONTS.get(name)
    if not path:
        return None
    if Path(path).exists():
        return path
    return None


@app.post("/generate")
def generate_pdf():
    if "csv" not in request.files:
        return jsonify({"error": "CSV file missing"}), 400

    csv_file = request.files["csv"]
    if not csv_file.filename:
        return jsonify({"error": "CSV file missing"}), 400

    font_name = request.form.get("fontName", "Helvetica")
    script_font = request.form.get("scriptFont", "AppleChancery")
    shift_left = float(request.form.get("shiftLeft", "0.5"))
    shift_down = float(request.form.get("shiftDown", "0.0"))
    font_size = float(request.form.get("fontSize", "9"))
    output_name = request.form.get("outputName", "filled_awards.pdf")

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
            template_path=Path("/Users/kevinwolf/Downloads/33006(18)CS Adventure-FillableCert.pdf"),
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
    app.run(port=5178, debug=True)
