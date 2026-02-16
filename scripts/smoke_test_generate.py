#!/usr/bin/env python3
from __future__ import annotations

import io
from pathlib import Path

from dev.cert_form_ui.server import app


def main() -> None:
    client = app.test_client()
    csv_path = Path("dev/cert_form_ui/cub_scout_award_template.csv")
    if not csv_path.exists():
        raise SystemExit(f"Missing CSV template: {csv_path}")

    with csv_path.open("rb") as f:
        payload = {
            "csv": (io.BytesIO(f.read()), "input.csv"),
            "fontName": "Merriweather",
            "scriptFont": "DancingScript",
            "shiftLeft": "0.5",
            "shiftDown": "0.5",
            "fontSize": "14",
            "scriptFontSize": "24",
            "outputName": "ci_smoke.pdf",
        }
        response = client.post("/generate", data=payload, content_type="multipart/form-data")

    if response.status_code != 200:
        raise SystemExit(f"Smoke test failed: status={response.status_code}")
    if response.headers.get("Content-Type") != "application/pdf":
        raise SystemExit(f"Smoke test failed: content-type={response.headers.get('Content-Type')}")
    if len(response.data) < 2048:
        raise SystemExit(f"Smoke test failed: output too small ({len(response.data)} bytes)")

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
