# AGENTS

## Scope
This repo contains a PDF certificate generator and a local web UI.

## Key Paths
- `dev/fill_cub_scout_certs.py`: CSV -> PDF generator
- `dev/cert_form_ui/`: Frontend + Flask backend
- `dev/cert_form_ui/index.html`: home page
- `dev/cert_form_ui/adventures.html`: adventures generator page
- `dev/cert_form_ui/ranks.html`: ranks page
- `dev/cert_form_ui/nav.js`: shared hamburger navigation logic
- `dev/cert_form_ui/cub_scout_award_template.csv`: CSV template
- `dev/cert_form_ui/wolf_rank_template.csv`: initial Wolf rank CSV template

## Local Run
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
cubscout-awards-web
```
Open `http://localhost:5178`.

## Local CLI
```sh
cubscout-awards --csv /path/to/awards.csv --output /path/to/filled_awards.pdf
```

## Notes
- The default PDF template is `assets/templates/cub_scout_award_certificate.pdf`.
- `CERT_TEMPLATE_PATH` overrides the server template.
- `--template` overrides the CLI template.
- For local installs, use editable mode (`pip install -e .`) so `assets/` files remain available.
- UI supports CSV preflight validation and output modes (`combined_pdf`, `per_scout_zip`).
- UI is split into pages (`/`, `/adventures`, `/ranks`) with top-right hamburger navigation between Adventures and Ranks.
- Ranks page currently includes Wolf template download and placeholders for Lion/Tiger/Bear/Webelo/Arrow of Light templates.
- Backend applies per-IP rate limiting:
  - `RATE_LIMIT_GENERATE_PER_MINUTE` (default `12`)
  - `RATE_LIMIT_VALIDATE_PER_MINUTE` (default `30`)
- CI workflow: `.github/workflows/ci.yml` runs install + smoke checks.
- Deploy workflow: `.github/workflows/deploy-cloud-run.yml` deploys to Cloud Run on `main` when required GitHub Variables/Secrets are set.
- Package publish workflow: `.github/workflows/publish-ghcr.yml` publishes `ghcr.io/<owner>/cubscoutawards` on pushes to `main`.
