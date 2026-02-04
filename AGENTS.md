# AGENTS

## Scope
This repo contains a PDF certificate generator and a local web UI.

## Key Paths
- `dev/fill_cub_scout_certs.py`: CSV -> PDF generator
- `dev/cert_form_ui/`: Frontend + Flask backend
- `dev/cert_form_ui/cub_scout_award_template.csv`: CSV template

## Local Run
```sh
python /Users/kevinwolf/cubscoutawards/dev/cert_form_ui/server.py
```
Open `http://localhost:5178`.

## Notes
- The PDF template path is hardcoded in `dev/cert_form_ui/server.py`.
- The CLI default template path is in `dev/fill_cub_scout_certs.py`.
- No formal tests.
