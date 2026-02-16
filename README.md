# Cub Scout Awards

Generate Cub Scout award certificates from a CSV and a fillable PDF template. Includes a local web UI for CSV upload, live preview, font selection, and PDF generation.

## What's Included
- `dev/fill_cub_scout_certs.py`: CSV -> filled PDF generator
- `dev/cert_form_ui/`: Frontend + Flask backend
  - `index.html`, `styles.css`, `app.js`
  - `server.py`
  - `cub_scout_award_template.csv`

## Requirements
- Python 3
- Packages: `pypdf`, `reportlab`, `flask`, `gunicorn`

## Setup (Local)
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run the Web UI
```sh
python /Users/kevinwolf/cubscoutawards/dev/cert_form_ui/server.py
```
Open `http://localhost:5178`.

## CSV Format
Headers required:
```
Date,Pack Number,Scout Name,Award Name,Den Leader,Cubmaster
```
Download the template from the UI or use:
`dev/cert_form_ui/cub_scout_award_template.csv`.

## Template PDF
The generator uses a fillable PDF template. The path is currently hardcoded in:
- `assets/templates/cub_scout_award_certificate.pdf` (default)

You can override with:
- `CERT_TEMPLATE_PATH` (web server env var)
- `--template` (CLI flag)

## CLI Usage
```sh
python /Users/kevinwolf/cubscoutawards/dev/fill_cub_scout_certs.py \
  --csv "/path/to/awards.csv" \
  --output "/path/to/filled_awards.pdf" \
  --shift-left-inch 0.5 \
  --shift-down-inch 0.5
```

## Notes
- Dates are normalized to `MM/DD/YYYY`.
- Fields are centered inside their boxes.
- Den Leader and Cubmaster use a cursive font when available.
- You can set both a main font size and a separate script font size for signatures.
- Additional Google Fonts are available in the UI and rendered in PDFs via bundled font files in `assets/fonts`.

## Deploy to Google Cloud Run (Public)
1. Set your project:
```sh
gcloud config set project YOUR_PROJECT_ID
```
2. Enable required services:
```sh
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```
3. Deploy:
```sh
gcloud run deploy cubscoutawards \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```
4. The command returns a public URL when deployment is complete.
