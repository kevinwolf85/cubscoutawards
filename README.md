# Cub Scout Awards

Generate Cub Scout award certificates from a CSV and a fillable PDF template. Includes a local web UI for CSV upload, font selection, and PDF generation.

## What's Included
- `dev/fill_cub_scout_certs.py`: CSV -> filled PDF generator
- `dev/cert_form_ui/`: Frontend + Flask backend
  - `index.html`, `styles.css`, `app.js`
  - `server.py`
  - `cub_scout_award_template.csv`

## Requirements
- Python 3
- Packages: `pypdf`, `reportlab`, `flask`

## Setup (Local)
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install pypdf reportlab flask
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
- `dev/cert_form_ui/server.py`
- `dev/fill_cub_scout_certs.py` (CLI default)

Update those paths if your template lives elsewhere.

## CLI Usage
```sh
python /Users/kevinwolf/cubscoutawards/dev/fill_cub_scout_certs.py \
  --csv "/path/to/awards.csv" \
  --output "/path/to/filled_awards.pdf" \
  --shift-left-inch 0.5 \
  --shift-down-inch 0
```

## Notes
- Dates are normalized to `MM/DD/YYYY`.
- Fields are centered inside their boxes.
- Den Leader and Cubmaster use a cursive font when available.
