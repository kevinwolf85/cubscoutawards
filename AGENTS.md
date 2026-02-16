# AGENTS

## Scope
This repo contains a PDF certificate generator and a local web UI.

## Key Paths
- `dev/fill_cub_scout_certs.py`: CSV -> PDF generator
- `dev/fill_cub_scout_rank_cards.py`: coordinate-based renderer for non-fillable rank card templates
- `dev/cert_form_ui/`: Frontend + Flask backend
- `dev/cert_form_ui/index.html`: home page
- `dev/cert_form_ui/adventures.html`: adventures generator page
- `dev/cert_form_ui/ranks.html`: ranks page
- `dev/cert_form_ui/nav.js`: shared hamburger navigation logic
- `dev/cert_form_ui/app.js`: shared generator UI logic for Adventures and Ranks
- `dev/cert_form_ui/cub_scout_award_template.csv`: CSV template
- `dev/cert_form_ui/rank_template.csv`: shared CSV template for all ranks
- `dev/cert_form_ui/wolf_rank_template.csv`: initial Wolf rank CSV template
- `assets/templates/wolf_rank_card.pdf`: default Wolf rank template

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
- The default Wolf rank template is `assets/templates/wolf_rank_card.pdf`.
- `CERT_TEMPLATE_PATH` overrides the server template.
- `--template` overrides the CLI template.
- For local installs, use editable mode (`pip install -e .`) so `assets/` files remain available.
- UI supports CSV preflight validation and output modes (`combined_pdf`, `per_scout_zip`) on both Adventures and Ranks pages.
- UI is split into pages (`/`, `/adventures`, `/ranks`) with top-right hamburger navigation that stays hidden until clicked.
- Ranks page mirrors Adventures controls and adds a rank selector (`Lion`, `Tiger`, `Wolf`, `Bear`, `Webelo`, `Arrow of Light`) to drive template selection.
- Backend applies per-IP rate limiting:
  - `RATE_LIMIT_GENERATE_PER_MINUTE` (default `12`)
  - `RATE_LIMIT_VALIDATE_PER_MINUTE` (default `30`)
- Optional per-rank server template overrides:
  - `CERT_TEMPLATE_PATH_LION`, `CERT_TEMPLATE_PATH_TIGER`, `CERT_TEMPLATE_PATH_WOLF`
  - `CERT_TEMPLATE_PATH_BEAR`, `CERT_TEMPLATE_PATH_WEBELO`, `CERT_TEMPLATE_PATH_ARROW_OF_LIGHT`
- Rank generation auto-detects non-fillable templates and falls back to `fill_rank_cards`.
- Wolf rank cards render `Den Number`, `Pack Number`, `Date`, `Scout Name`, `Den Leader`, and `Cubmaster` via tuned coordinate boxes with centered text.
- Wolf rank signature rendering caps script size for legibility on the small printed lines.
- CI workflow: `.github/workflows/ci.yml` runs install + smoke checks.
- Deploy workflow: `.github/workflows/deploy-cloud-run.yml` deploys to Cloud Run on `main` when required GitHub Variables/Secrets are set.
- Package publish workflow: `.github/workflows/publish-ghcr.yml` publishes `ghcr.io/<owner>/cubscoutawards` on pushes to `main`.
