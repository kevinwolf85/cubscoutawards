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

FONT_CHOICES = {
    "Helvetica": {"pdf_name": "Helvetica", "paths": []},
    "TimesRoman": {"pdf_name": "Times-Roman", "paths": []},
    "Courier": {"pdf_name": "Courier", "paths": []},
    "DejaVuSerif": {
        "pdf_name": "DejaVuSerif",
        "paths": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
        ],
    },
    "DejaVuSans": {
        "pdf_name": "DejaVuSans",
        "paths": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Verdana.ttf",
        ],
    },
    "DejaVuSansMono": {
        "pdf_name": "DejaVuSansMono",
        "paths": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
        ],
    },
}

SCRIPT_FONT_CHOICES = {
    "None": {"pdf_name": None, "paths": []},
    "DejaVuSerifItalic": {
        "pdf_name": "DejaVuSerifItalic",
        "paths": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"],
    },
    "DejaVuSansOblique": {
        "pdf_name": "DejaVuSansOblique",
        "paths": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"],
    },
}

LEGACY_FONT_ALIASES = {
    "Times-Roman": "TimesRoman",
    "Georgia": "DejaVuSerif",
    "Verdana": "DejaVuSans",
    "Tahoma": "DejaVuSans",
    "TrebuchetMS": "DejaVuSans",
    "TimesNewRoman": "DejaVuSerif",
    "CourierNew": "DejaVuSansMono",
    "Geneva": "DejaVuSans",
    "Chalkduster": "DejaVuSans",
    "AppleChancery": "DejaVuSerifItalic",
    "BradleyHand": "DejaVuSerifItalic",
    "BrushScript": "DejaVuSerifItalic",
}


def _resolve_font_choice(choice_id: str, catalog: dict) -> tuple[Optional[str], Optional[str]]:
    resolved_id = LEGACY_FONT_ALIASES.get(choice_id, choice_id)
    choice = catalog.get(resolved_id)
    if not choice:
        return None, None
    pdf_name = choice["pdf_name"]
    if not pdf_name:
        return None, None
    if not choice["paths"]:
        return pdf_name, None
    for path in choice["paths"]:
        if Path(path).exists():
            return pdf_name, path
    return None, None


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

    font_choice = request.form.get("fontName", "Helvetica")
    script_choice = request.form.get("scriptFont", "DejaVuSerifItalic")
    shift_left = _parse_float(request.form.get("shiftLeft", "0.5"), fallback=0.5)
    shift_down = _parse_float(request.form.get("shiftDown", "0.5"), fallback=0.5)
    font_size = _parse_float(request.form.get("fontSize", "9"), fallback=9.0)
    output_name = _safe_output_name(request.form.get("outputName", "filled_awards.pdf"))

    if not TEMPLATE_PATH.exists():
        return jsonify({"error": "Template PDF not configured on server."}), 500

    font_name, font_file = _resolve_font_choice(font_choice, FONT_CHOICES)
    if not font_name:
        font_name = "Helvetica"
        font_file = None
    script_font_name, script_font_file = _resolve_font_choice(script_choice, SCRIPT_FONT_CHOICES)

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
            script_font_name=script_font_name,
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
