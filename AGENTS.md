# AGENTS

## Scope
This repo contains a PDF certificate generator and a local web UI.

## Key Paths
- `dev/fill_cub_scout_certs.py`: CSV -> PDF generator
- `dev/cert_form_ui/`: Frontend + Flask backend
- `dev/cert_form_ui/cub_scout_award_template.csv`: CSV template

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
- No formal tests.
