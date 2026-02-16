#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import os
import re
import tempfile
import time
import zipfile
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Optional

from flask import Flask, jsonify, request, send_file

UI_DIR = Path(__file__).resolve().parent
REPO_ROOT = UI_DIR.parent.parent
DEFAULT_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "cub_scout_award_certificate.pdf"
FONTS_DIR = REPO_ROOT / "assets" / "fonts"
TEMPLATE_PATH = Path(os.environ.get("CERT_TEMPLATE_PATH", str(DEFAULT_TEMPLATE_PATH))).expanduser()

try:
    from dev.fill_cub_scout_certs import fill_certificates
except ModuleNotFoundError:
    # Fallback for direct script execution from source checkout.
    import sys

    DEV_DIR = REPO_ROOT / "dev"
    if str(DEV_DIR) not in sys.path:
        sys.path.insert(0, str(DEV_DIR))
    from fill_cub_scout_certs import fill_certificates  # type: ignore

app = Flask(__name__, static_folder=str(UI_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB CSV upload limit

REQUIRED_HEADERS = ["Date", "Pack Number", "Scout Name", "Award Name", "Den Leader", "Cubmaster"]
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y")
GENERATE_PER_MINUTE = int(os.environ.get("RATE_LIMIT_GENERATE_PER_MINUTE", "12"))
VALIDATE_PER_MINUTE = int(os.environ.get("RATE_LIMIT_VALIDATE_PER_MINUTE", "30"))

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
    "Alegreya": {"pdf_name": "Alegreya", "paths": [str(FONTS_DIR / "Alegreya-Regular.ttf")]},
    "Archivo": {"pdf_name": "Archivo", "paths": [str(FONTS_DIR / "Archivo-Regular.ttf")]},
    "FiraSans": {"pdf_name": "FiraSans", "paths": [str(FONTS_DIR / "FiraSans-Regular.ttf")]},
    "Bangers": {"pdf_name": "Bangers", "paths": [str(FONTS_DIR / "Bangers-Regular.ttf")]},
    "CabinSketch": {"pdf_name": "CabinSketch", "paths": [str(FONTS_DIR / "CabinSketch-Regular.ttf")]},
    "LilitaOne": {"pdf_name": "LilitaOne", "paths": [str(FONTS_DIR / "LilitaOne-Regular.ttf")]},
    "Righteous": {"pdf_name": "Righteous", "paths": [str(FONTS_DIR / "Righteous-Regular.ttf")]},
    "Oswald": {"pdf_name": "Oswald", "paths": [str(FONTS_DIR / "Oswald-Regular.ttf")]},
    "Montserrat": {"pdf_name": "Montserrat", "paths": [str(FONTS_DIR / "Montserrat-Regular.ttf")]},
    "Kanit": {"pdf_name": "Kanit", "paths": [str(FONTS_DIR / "Kanit-Regular.ttf")]},
    "Lora": {"pdf_name": "Lora", "paths": [str(FONTS_DIR / "Lora-Regular.ttf")]},
    "CrimsonPro": {"pdf_name": "CrimsonPro", "paths": [str(FONTS_DIR / "CrimsonPro-Regular.ttf")]},
    "IBMPlexSerif": {"pdf_name": "IBMPlexSerif", "paths": [str(FONTS_DIR / "IBMPlexSerif-Regular.ttf")]},
    "Merriweather": {"pdf_name": "Merriweather", "paths": [str(FONTS_DIR / "Merriweather-Regular.ttf")]},
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
    "PatrickHand": {"pdf_name": "PatrickHand", "paths": [str(FONTS_DIR / "PatrickHand-Regular.ttf")]},
    "PermanentMarker": {
        "pdf_name": "PermanentMarker",
        "paths": [str(FONTS_DIR / "PermanentMarker-Regular.ttf")],
    },
    "DancingScript": {"pdf_name": "DancingScript", "paths": [str(FONTS_DIR / "DancingScript-Regular.ttf")]},
    "Caveat": {"pdf_name": "Caveat", "paths": [str(FONTS_DIR / "Caveat-Regular.ttf")]},
    "KaushanScript": {
        "pdf_name": "KaushanScript",
        "paths": [str(FONTS_DIR / "KaushanScript-Regular.ttf")],
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
    "AppleChancery": "PatrickHand",
    "BradleyHand": "PatrickHand",
    "BrushScript": "PermanentMarker",
}


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            q = self._hits[key]
            cutoff = now - self.window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True


generate_limiter = SlidingWindowLimiter(GENERATE_PER_MINUTE)
validate_limiter = SlidingWindowLimiter(VALIDATE_PER_MINUTE)


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


def _safe_base_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", value.strip())
    return name.strip("._-") or "item"


def _safe_zip_name(value: str) -> str:
    filename = Path(value or "").name
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    if not filename:
        filename = "filled_awards.zip"
    if not filename.lower().endswith(".zip"):
        filename = f"{Path(filename).stem}.zip"
    return filename


def _client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _rate_limited_response() -> tuple[dict, int]:
    return {"error": "Rate limit exceeded. Please wait and try again."}, 429


def _is_valid_date(value: str) -> bool:
    value = (value or "").strip()
    if not value:
        return True
    for fmt in DATE_FORMATS:
        try:
            time.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _parse_csv_bytes(csv_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], []
    rows = [row for row in reader if any((v or "").strip() for v in row.values())]
    return list(reader.fieldnames), rows


def _build_validation_report(fieldnames: list[str], rows: list[dict[str, str]]) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [h for h in REQUIRED_HEADERS if h not in fieldnames]
    if missing:
        errors.append(f"Missing required headers: {', '.join(missing)}")
    if not rows:
        errors.append("CSV has no data rows.")

    for idx, row in enumerate(rows, start=2):
        scout_name = (row.get("Scout Name") or "").strip()
        award_name = (row.get("Award Name") or "").strip()
        pack_number = (row.get("Pack Number") or "").strip()
        date_value = (row.get("Date") or "").strip()
        if not scout_name:
            errors.append(f"Row {idx}: Scout Name is required.")
        if not award_name:
            errors.append(f"Row {idx}: Award Name is required.")
        if not pack_number:
            warnings.append(f"Row {idx}: Pack Number is empty.")
        if date_value and not _is_valid_date(date_value):
            warnings.append(f"Row {idx}: Date '{date_value}' is not in a recognized format.")

    return {
        "header_count": len(fieldnames),
        "row_count": len(rows),
        "errors": errors,
        "warnings": warnings,
        "ok": len(errors) == 0,
    }


def _csv_missing_response() -> tuple[dict, int]:
    return {"error": "CSV file missing"}, 400


@app.post("/validate-csv")
def validate_csv():
    if not validate_limiter.allow(_client_ip()):
        payload, code = _rate_limited_response()
        return jsonify(payload), code

    if "csv" not in request.files:
        payload, code = _csv_missing_response()
        return jsonify(payload), code
    csv_file = request.files["csv"]
    if not csv_file.filename:
        payload, code = _csv_missing_response()
        return jsonify(payload), code

    try:
        csv_bytes = csv_file.read()
        fieldnames, rows = _parse_csv_bytes(csv_bytes)
    except UnicodeDecodeError:
        return jsonify({"error": "CSV must be UTF-8 encoded."}), 400

    report = _build_validation_report(fieldnames, rows)
    return jsonify(report)


@app.post("/generate")
def generate_pdf():
    if not generate_limiter.allow(_client_ip()):
        payload, code = _rate_limited_response()
        return jsonify(payload), code

    if "csv" not in request.files:
        payload, code = _csv_missing_response()
        return jsonify(payload), code

    csv_file = request.files["csv"]
    if not csv_file.filename:
        payload, code = _csv_missing_response()
        return jsonify(payload), code

    font_choice = request.form.get("fontName", "Helvetica")
    script_choice = request.form.get("scriptFont", "PatrickHand")
    shift_left = _parse_float(request.form.get("shiftLeft", "0.5"), fallback=0.5)
    shift_down = _parse_float(request.form.get("shiftDown", "0.5"), fallback=0.5)
    font_size = _parse_float(request.form.get("fontSize", "14"), fallback=14.0)
    script_font_size = _parse_float(request.form.get("scriptFontSize", "24"), fallback=24.0)
    output_mode = request.form.get("outputMode", "combined_pdf")
    output_name = _safe_output_name(request.form.get("outputName", "filled_awards.pdf"))

    if not TEMPLATE_PATH.exists():
        return jsonify({"error": "Template PDF not configured on server."}), 500

    try:
        csv_bytes = csv_file.read()
        fieldnames, rows = _parse_csv_bytes(csv_bytes)
    except UnicodeDecodeError:
        return jsonify({"error": "CSV must be UTF-8 encoded."}), 400

    report = _build_validation_report(fieldnames, rows)
    if not report["ok"]:
        return jsonify({"error": "CSV validation failed.", "report": report}), 400

    font_name, font_file = _resolve_font_choice(font_choice, FONT_CHOICES)
    if not font_name:
        font_name = "Helvetica"
        font_file = None
    script_font_name, script_font_file = _resolve_font_choice(script_choice, SCRIPT_FONT_CHOICES)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        csv_path = tmpdir_path / "input.csv"
        csv_path.write_bytes(csv_bytes)

        if output_mode == "per_scout_zip":
            zip_name = _safe_zip_name(request.form.get("outputName", "scout_awards.zip"))
            zip_path = tmpdir_path / zip_name
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for i, row in enumerate(rows, start=1):
                    scout = _safe_base_name(row.get("Scout Name", "scout"))
                    award = _safe_base_name(row.get("Award Name", "award"))
                    file_stem = f"{i:03d}_{scout}_{award}"
                    row_csv = tmpdir_path / f"{file_stem}.csv"
                    row_pdf = tmpdir_path / f"{file_stem}.pdf"
                    with row_csv.open("w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=REQUIRED_HEADERS)
                        writer.writeheader()
                        writer.writerow({k: row.get(k, "") for k in REQUIRED_HEADERS})
                    fill_certificates(
                        csv_path=row_csv,
                        output_path=row_pdf,
                        template_path=TEMPLATE_PATH,
                        shift_left_inch=shift_left,
                        shift_down_inch=shift_down,
                        font_name=font_name,
                        script_font_name=script_font_name,
                        font_size=font_size,
                        script_font_size=script_font_size,
                        font_file=font_file,
                        script_font_file=script_font_file,
                    )
                    zf.write(row_pdf, arcname=row_pdf.name)

            return send_file(
                zip_path,
                as_attachment=True,
                download_name=zip_name,
                mimetype="application/zip",
            )

        out_path = tmpdir_path / output_name
        fill_certificates(
            csv_path=csv_path,
            output_path=out_path,
            template_path=TEMPLATE_PATH,
            shift_left_inch=shift_left,
            shift_down_inch=shift_down,
            font_name=font_name,
            script_font_name=script_font_name,
            font_size=font_size,
            script_font_size=script_font_size,
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


@app.get("/adventures")
def adventures_page():
    return app.send_static_file("adventures.html")


@app.get("/ranks")
def ranks_page():
    return app.send_static_file("ranks.html")


@app.get("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.png")


def main() -> None:
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5178")), debug=False)


if __name__ == "__main__":
    main()
