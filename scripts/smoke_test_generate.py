#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from dev.cert_form_ui.server import app


def main() -> None:
    client = app.test_client()
    csv_path = Path("dev/cert_form_ui/cub_scout_award_template.csv")
    if not csv_path.exists():
        raise SystemExit(f"Missing CSV template: {csv_path}")

    with csv_path.open("rb") as f:
        csv_bytes = f.read()

    validate_payload = {"csv": (io.BytesIO(csv_bytes), "input.csv")}
    validate_response = client.post("/validate-csv", data=validate_payload, content_type="multipart/form-data")
    if validate_response.status_code != 200:
        raise SystemExit(f"Validate smoke test failed: status={validate_response.status_code}")

    payload = {
        "csv": (io.BytesIO(csv_bytes), "input.csv"),
        "fontName": "Merriweather",
        "scriptFont": "DancingScript",
        "shiftLeft": "0.5",
        "shiftDown": "0.5",
        "fontSize": "14",
        "scriptFontSize": "24",
        "outputName": "ci_smoke.pdf",
        "outputMode": "combined_pdf",
    }
    response = client.post("/generate", data=payload, content_type="multipart/form-data")

    if response.status_code != 200:
        raise SystemExit(f"PDF smoke test failed: status={response.status_code}")
    if response.headers.get("Content-Type") != "application/pdf":
        raise SystemExit(f"PDF smoke test failed: content-type={response.headers.get('Content-Type')}")
    if len(response.data) < 2048:
        raise SystemExit(f"PDF smoke test failed: output too small ({len(response.data)} bytes)")

    zip_payload = {
        "csv": (io.BytesIO(csv_bytes), "input.csv"),
        "fontName": "Merriweather",
        "scriptFont": "DancingScript",
        "shiftLeft": "0.5",
        "shiftDown": "0.5",
        "fontSize": "14",
        "scriptFontSize": "24",
        "outputName": "ci_smoke.zip",
        "outputMode": "per_scout_zip",
    }
    zip_response = client.post("/generate", data=zip_payload, content_type="multipart/form-data")

    if zip_response.status_code != 200:
        raise SystemExit(f"ZIP smoke test failed: status={zip_response.status_code}")
    if zip_response.headers.get("Content-Type") != "application/zip":
        raise SystemExit(f"ZIP smoke test failed: content-type={zip_response.headers.get('Content-Type')}")
    if len(zip_response.data) < 2048:
        raise SystemExit(f"ZIP smoke test failed: output too small ({len(zip_response.data)} bytes)")

    zf = zipfile.ZipFile(io.BytesIO(zip_response.data))
    if not zf.namelist():
        raise SystemExit("ZIP smoke test failed: archive is empty")

    print("Smoke tests passed.")


if __name__ == "__main__":
    main()
