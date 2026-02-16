# Cub Scout Awards

Generate Cub Scout award certificates from a CSV and a fillable PDF template. Includes a local web UI for CSV upload, live preview, font selection, and PDF generation.

## What's Included
- `dev/fill_cub_scout_certs.py`: CSV -> filled PDF generator
- `dev/fill_cub_scout_rank_cards.py`: CSV -> rendered rank-card PDF generator for non-fillable rank templates
- `dev/cert_form_ui/`: Frontend + Flask backend
  - `index.html` (home), `adventures.html`, `ranks.html`
  - `styles.css`, `nav.js`, `app.js`
  - `server.py`
  - `cub_scout_award_template.csv`
- `assets/templates/wolf_rank_card.pdf`: Wolf rank template (non-fillable)

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
Pages:
- Home: `/`
- Adventures: `/adventures`
- Ranks: `/ranks`

Navigation:
- A hamburger menu is available at the top-right of each page to switch between Home, Adventures, and Ranks.

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

Rank template currently available:
- `dev/cert_form_ui/rank_template.csv`
  - Shared template for Lion, Tiger, Wolf, Bear, Webelo, and Arrow of Light.
- `dev/cert_form_ui/wolf_rank_template.csv`
  - Wolf-focused sample CSV template.
  - Rank workflow accepts `Rank` (or `Award Name`) and maps it to generated output text.

## Template PDF
The generator uses a fillable PDF template. The path is currently hardcoded in:
- `assets/templates/cub_scout_award_certificate.pdf` (default)
- `assets/templates/lion_rank_card.pdf` (default for `Lion` in rank workflow)
- `assets/templates/tiger_rank_card.pdf` (default for `Tiger` in rank workflow)
- `assets/templates/wolf_rank_card.pdf` (default for `Wolf` in rank workflow)
- `assets/templates/bear_rank_card.pdf` (default for `Bear` in rank workflow)
- `assets/templates/webelo_rank_card.pdf` (default for `Webelo` in rank workflow)
- `assets/templates/arrow_of_light_rank_card.pdf` (default for `Arrow of Light` in rank workflow)

You can override with:
- `CERT_TEMPLATE_PATH` (web server env var)
- `--template` (CLI flag)

Optional per-rank server template overrides:
- `CERT_TEMPLATE_PATH_LION`
- `CERT_TEMPLATE_PATH_TIGER`
- `CERT_TEMPLATE_PATH_WOLF`
- `CERT_TEMPLATE_PATH_BEAR`
- `CERT_TEMPLATE_PATH_WEBELO`
- `CERT_TEMPLATE_PATH_ARROW_OF_LIGHT`

When a selected rank template has no AcroForm fields, the server automatically falls back to coordinate-based rendering (`fill_rank_cards`).
Rank outputs are rotated by default for print orientation (`RANK_OUTPUT_ROTATION_DEGREES=90`).

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
- CSV preflight validation is available in the UI (`Validate CSV`) and via `POST /validate-csv`.
- Output modes:
  - `combined_pdf` (single merged PDF)
  - `per_scout_zip` (ZIP containing one PDF per scout)
- Ranks page uses the same controls as Adventures (CSV upload, fonts, shifts, validation, output modes) plus a `Rank` selector that drives template selection.
- Wolf rank rendering uses tuned coordinates and centered text boxes for `Den Number`, `Pack Number`, `Date`, `Scout Name`, `Den Leader`, and `Cubmaster` so placement behavior matches Adventures more closely.
- On Wolf rank cards, signature text size is capped for readability to avoid collisions with static labels.
- Basic per-IP rate limiting is enabled for public safety:
  - `RATE_LIMIT_GENERATE_PER_MINUTE` (default `12`)
  - `RATE_LIMIT_VALIDATE_PER_MINUTE` (default `30`)

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
- `.github/workflows/publish-ghcr.yml`: publish container image to GitHub Packages (GHCR)

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
- GHCR images are published to `ghcr.io/<owner>/cubscoutawards` on pushes to `main`.
