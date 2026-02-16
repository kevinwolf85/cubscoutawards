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
from pypdf import PdfReader, PdfWriter

UI_DIR = Path(__file__).resolve().parent
REPO_ROOT = UI_DIR.parent.parent
DEFAULT_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "cub_scout_award_certificate.pdf"
DEFAULT_LION_RANK_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "lion_rank_card.pdf"
DEFAULT_TIGER_RANK_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "tiger_rank_card.pdf"
DEFAULT_WOLF_RANK_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "wolf_rank_card.pdf"
DEFAULT_BEAR_RANK_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "bear_rank_card.pdf"
DEFAULT_WEBELO_RANK_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "webelo_rank_card.pdf"
DEFAULT_ARROW_OF_LIGHT_RANK_TEMPLATE_PATH = REPO_ROOT / "assets" / "templates" / "arrow_of_light_rank_card.pdf"
FONTS_DIR = REPO_ROOT / "assets" / "fonts"
TEMPLATE_PATH = Path(os.environ.get("CERT_TEMPLATE_PATH", str(DEFAULT_TEMPLATE_PATH))).expanduser()
RANK_TEMPLATE_PATHS = {
    "Lion": Path(os.environ.get("CERT_TEMPLATE_PATH_LION", str(DEFAULT_LION_RANK_TEMPLATE_PATH))).expanduser(),
    "Tiger": Path(os.environ.get("CERT_TEMPLATE_PATH_TIGER", str(DEFAULT_TIGER_RANK_TEMPLATE_PATH))).expanduser(),
    "Wolf": Path(
        os.environ.get("CERT_TEMPLATE_PATH_WOLF", str(DEFAULT_WOLF_RANK_TEMPLATE_PATH))
    ).expanduser(),
    "Bear": Path(os.environ.get("CERT_TEMPLATE_PATH_BEAR", str(DEFAULT_BEAR_RANK_TEMPLATE_PATH))).expanduser(),
    "Webelo": Path(os.environ.get("CERT_TEMPLATE_PATH_WEBELO", str(DEFAULT_WEBELO_RANK_TEMPLATE_PATH))).expanduser(),
    "Arrow of Light": Path(
        os.environ.get("CERT_TEMPLATE_PATH_ARROW_OF_LIGHT", str(DEFAULT_ARROW_OF_LIGHT_RANK_TEMPLATE_PATH))
    ).expanduser(),
}

try:
    from dev.fill_cub_scout_certs import fill_certificates
    from dev.fill_cub_scout_rank_cards import fill_rank_cards
except ModuleNotFoundError:
    # Fallback for direct script execution from source checkout.
    import sys

    DEV_DIR = REPO_ROOT / "dev"
    if str(DEV_DIR) not in sys.path:
        sys.path.insert(0, str(DEV_DIR))
    from fill_cub_scout_certs import fill_certificates  # type: ignore
    from fill_cub_scout_rank_cards import fill_rank_cards  # type: ignore

app = Flask(__name__, static_folder=str(UI_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB CSV upload limit

GENERATOR_HEADERS = ["Date", "Pack Number", "Den Number", "Scout Name", "Award Name", "Den Leader", "Cubmaster"]
COMMON_REQUIRED_HEADERS = ["Date", "Pack Number", "Scout Name", "Den Leader", "Cubmaster"]
ADVENTURE_REQUIRED_HEADERS = COMMON_REQUIRED_HEADERS + ["Award Name"]
RANK_REQUIRED_HEADERS = COMMON_REQUIRED_HEADERS + ["Rank"]
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y")
GENERATE_PER_MINUTE = int(os.environ.get("RATE_LIMIT_GENERATE_PER_MINUTE", "12"))
VALIDATE_PER_MINUTE = int(os.environ.get("RATE_LIMIT_VALIDATE_PER_MINUTE", "30"))
RANK_OUTPUT_ROTATION_DEGREES = int(os.environ.get("RANK_OUTPUT_ROTATION_DEGREES", "90")) % 360

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
_template_field_support_cache: dict[str, bool] = {}


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


def _canonical_rank(value: str) -> str:
    raw = (value or "").strip().lower()
    aliases = {
        "lion": "Lion",
        "tiger": "Tiger",
        "wolf": "Wolf",
        "bear": "Bear",
        "webelo": "Webelo",
        "webelos": "Webelo",
        "arrow of light": "Arrow of Light",
        "arrow_of_light": "Arrow of Light",
        "aol": "Arrow of Light",
    }
    return aliases.get(raw, "Wolf")


def _selected_template(workflow: str, selected_rank: str) -> Path:
    if workflow != "ranks":
        return TEMPLATE_PATH
    rank_key = _canonical_rank(selected_rank)
    rank_template = RANK_TEMPLATE_PATHS.get(rank_key, TEMPLATE_PATH)
    if rank_template.exists():
        return rank_template
    return TEMPLATE_PATH


def _template_supports_field_fill(template_path: Path) -> bool:
    key = str(template_path.resolve())
    cached = _template_field_support_cache.get(key)
    if cached is not None:
        return cached

    try:
        reader = PdfReader(str(template_path))
        page = reader.pages[0]
        annots = page.get("/Annots")
        if annots and len(annots.get_object()) > 0:
            _template_field_support_cache[key] = True
            return True
        acroform = reader.trailer["/Root"].get("/AcroForm")
        if acroform:
            fields = acroform.get_object().get("/Fields", [])
            supported = len(fields) > 0
            _template_field_support_cache[key] = supported
            return supported
    except Exception:
        pass

    _template_field_support_cache[key] = False
    return False


def _normalize_rows_for_generator(
    rows: list[dict[str, str]], workflow: str, selected_rank: str
) -> list[dict[str, str]]:
    normalized_rows: list[dict[str, str]] = []
    canonical_rank = _canonical_rank(selected_rank) if workflow == "ranks" else ""
    for row in rows:
        award_name = (row.get("Award Name") or "").strip()
        rank_name = (row.get("Rank") or "").strip()
        if workflow == "ranks":
            award_name = rank_name or canonical_rank or award_name
        normalized_rows.append(
            {
                "Date": (row.get("Date") or "").strip(),
                "Pack Number": (row.get("Pack Number") or "").strip(),
                "Den Number": (row.get("Den Number") or row.get("Den No.") or "").strip(),
                "Scout Name": (row.get("Scout Name") or "").strip(),
                "Award Name": award_name,
                "Den Leader": (row.get("Den Leader") or "").strip(),
                "Cubmaster": (row.get("Cubmaster") or "").strip(),
            }
        )
    return normalized_rows


def _parse_csv_bytes(csv_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], []
    rows = [row for row in reader if any((v or "").strip() for v in row.values())]
    return list(reader.fieldnames), rows


def _normalize_pdf_rotation_in_place(pdf_path: Path, target_rotation: int) -> None:
    target = target_rotation % 360
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for page in reader.pages:
        current = int(page.get("/Rotate") or 0) % 360
        delta = (target - current) % 360
        if delta:
            page.rotate(delta)
        writer.add_page(page)
    with pdf_path.open("wb") as f:
        writer.write(f)


def _build_validation_report(
    fieldnames: list[str], rows: list[dict[str, str]], workflow: str, selected_rank: str
) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    required_headers = ADVENTURE_REQUIRED_HEADERS if workflow != "ranks" else RANK_REQUIRED_HEADERS
    missing = [h for h in required_headers if h not in fieldnames]
    if workflow == "ranks" and "Rank" in missing and selected_rank:
        missing.remove("Rank")
    if missing:
        errors.append(f"Missing required headers: {', '.join(missing)}")
    if not rows:
        errors.append("CSV has no data rows.")

    rank_fallback = _canonical_rank(selected_rank) if workflow == "ranks" else ""
    for idx, row in enumerate(rows, start=2):
        scout_name = (row.get("Scout Name") or "").strip()
        award_name = (row.get("Award Name") or "").strip()
        if workflow == "ranks":
            award_name = (row.get("Rank") or "").strip() or rank_fallback or award_name
        pack_number = (row.get("Pack Number") or "").strip()
        date_value = (row.get("Date") or "").strip()
        if not scout_name:
            errors.append(f"Row {idx}: Scout Name is required.")
        if not award_name:
            label = "Rank" if workflow == "ranks" else "Award Name"
            errors.append(f"Row {idx}: {label} is required.")
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

    workflow = request.form.get("workflow", "adventures")
    selected_rank = request.form.get("rank", "")

    try:
        csv_bytes = csv_file.read()
        fieldnames, rows = _parse_csv_bytes(csv_bytes)
    except UnicodeDecodeError:
        return jsonify({"error": "CSV must be UTF-8 encoded."}), 400

    report = _build_validation_report(fieldnames, rows, workflow=workflow, selected_rank=selected_rank)
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
    workflow = request.form.get("workflow", "adventures")
    selected_rank = request.form.get("rank", "")
    output_name = _safe_output_name(request.form.get("outputName", "filled_awards.pdf"))
    template_path = _selected_template(workflow, selected_rank)

    if not template_path.exists():
        return jsonify({"error": "Template PDF not configured on server."}), 500

    try:
        csv_bytes = csv_file.read()
        fieldnames, rows = _parse_csv_bytes(csv_bytes)
    except UnicodeDecodeError:
        return jsonify({"error": "CSV must be UTF-8 encoded."}), 400

    report = _build_validation_report(fieldnames, rows, workflow=workflow, selected_rank=selected_rank)
    if not report["ok"]:
        return jsonify({"error": "CSV validation failed.", "report": report}), 400
    normalized_rows = _normalize_rows_for_generator(rows, workflow=workflow, selected_rank=selected_rank)
    use_rank_layout = workflow == "ranks" and not _template_supports_field_fill(template_path)
    fill_function = fill_rank_cards if use_rank_layout else fill_certificates

    font_name, font_file = _resolve_font_choice(font_choice, FONT_CHOICES)
    if not font_name:
        font_name = "Helvetica"
        font_file = None
    script_font_name, script_font_file = _resolve_font_choice(script_choice, SCRIPT_FONT_CHOICES)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        csv_path = tmpdir_path / "input.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=GENERATOR_HEADERS)
            writer.writeheader()
            for row in normalized_rows:
                writer.writerow({k: row.get(k, "") for k in GENERATOR_HEADERS})

        if output_mode == "per_scout_zip":
            zip_name = _safe_zip_name(request.form.get("outputName", "scout_awards.zip"))
            zip_path = tmpdir_path / zip_name
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for i, row in enumerate(normalized_rows, start=1):
                    scout = _safe_base_name(row.get("Scout Name", "scout"))
                    award = _safe_base_name(row.get("Award Name", "award"))
                    file_stem = f"{i:03d}_{scout}_{award}"
                    row_csv = tmpdir_path / f"{file_stem}.csv"
                    row_pdf = tmpdir_path / f"{file_stem}.pdf"
                    with row_csv.open("w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=GENERATOR_HEADERS)
                        writer.writeheader()
                        writer.writerow({k: row.get(k, "") for k in GENERATOR_HEADERS})
                    fill_function(
                        csv_path=row_csv,
                        output_path=row_pdf,
                        template_path=template_path,
                        shift_left_inch=shift_left,
                        shift_down_inch=shift_down,
                        font_name=font_name,
                        script_font_name=script_font_name,
                        font_size=font_size,
                        script_font_size=script_font_size,
                        font_file=font_file,
                        script_font_file=script_font_file,
                    )
                    if workflow == "ranks":
                        _normalize_pdf_rotation_in_place(row_pdf, RANK_OUTPUT_ROTATION_DEGREES)
                    zf.write(row_pdf, arcname=row_pdf.name)

            return send_file(
                zip_path,
                as_attachment=True,
                download_name=zip_name,
                mimetype="application/zip",
            )

        out_path = tmpdir_path / output_name
        fill_function(
            csv_path=csv_path,
            output_path=out_path,
            template_path=template_path,
            shift_left_inch=shift_left,
            shift_down_inch=shift_down,
            font_name=font_name,
            script_font_name=script_font_name,
            font_size=font_size,
            script_font_size=script_font_size,
            font_file=font_file,
            script_font_file=script_font_file,
        )
        if workflow == "ranks":
            _normalize_pdf_rotation_in_place(out_path, RANK_OUTPUT_ROTATION_DEGREES)

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
