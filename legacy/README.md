# Legacy code

Kept for reference only. Not part of any supported entry point and not
exercised by the test suite.

- `openrouter_cli_legacy.py` — the original OpenRouter CLI. Superseded by
  `bin/openrouter_cli.py`, which uses the shared `openrouter_service` layer.

The original Dash web app (`app.py`) was removed in commit 11b01f7
("Swap Dash for Flask"); `app_flask.py` is the only web interface.
