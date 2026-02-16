# Cub Scout Awards

Generate Cub Scout award certificates from a CSV and a fillable PDF template. Includes a local web UI for CSV upload, live preview, font selection, and PDF generation.

## What's Included
- `dev/fill_cub_scout_certs.py`: CSV -> filled PDF generator
- `dev/cert_form_ui/`: Frontend + Flask backend
  - `index.html`, `styles.css`, `app.js`
  - `server.py`
  - `cub_scout_award_template.csv`

## Requirements
- Python 3.10+

## Setup (Local Package Install)
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Run the Web UI
```sh
cubscout-awards-web
```
Open `http://localhost:5178`.

Alternative (without package entrypoint):
```sh
python dev/cert_form_ui/server.py
```

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
cubscout-awards \
  --csv "/path/to/awards.csv" \
  --output "/path/to/filled_awards.pdf" \
  --shift-left-inch 0.5 \
  --shift-down-inch 0.5
```

You can also provide custom font files:
```sh
cubscout-awards \
  --csv "/path/to/awards.csv" \
  --output "/path/to/filled_awards.pdf" \
  --font-name Merriweather \
  --font-file assets/fonts/Merriweather-Regular.ttf \
  --script-font-name DancingScript \
  --script-font-file assets/fonts/DancingScript-Regular.ttf
```

## Notes
- Dates are normalized to `MM/DD/YYYY`.
- Fields are centered inside their boxes.
- Den Leader and Cubmaster use a cursive font when available.
- You can set both a main font size and a separate script font size for signatures.
- Additional Google Fonts are available in the UI and rendered in PDFs via bundled font files in `assets/fonts`.
- For local install, use editable mode (`pip install -e .`) so template/font assets under `assets/` are available.

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

## GitHub Actions CI/CD
This repo includes:
- `.github/workflows/ci.yml`: install + smoke test on PRs/pushes
- `.github/workflows/deploy-cloud-run.yml`: deploy to Cloud Run on `main` (and manual dispatch)

### Required GitHub Variables
- `GCP_PROJECT_ID`: Google Cloud project ID
- `CLOUD_RUN_SERVICE`: Cloud Run service name (for example `cubscoutawards`)
- `CLOUD_RUN_REGION`: optional, defaults to `us-central1`
- `CLOUD_BUILD_SERVICE_ACCOUNT`: optional build service account email

### Required GitHub Secrets
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: Workload Identity Provider resource path
- `GCP_SERVICE_ACCOUNT`: service account email for deploy auth

### Notes
- Deploy workflow auto-skips when required auth/config values are missing.
- You can manually run deploy from the Actions tab using `workflow_dispatch`.
