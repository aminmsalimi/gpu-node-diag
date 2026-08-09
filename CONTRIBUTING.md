# Contributing

Contributions, bug reports, hardware testing, and diagnostic improvements are welcome.

Development setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -v
```

New diagnostic rules should include tests and should not modify system configuration unless the user explicitly requests a disruptive operation.
