"""Entry point for the PyInstaller build.
PyInstaller imports this file as a top-level script, so an absolute import
is required — the relative `.app` form does not work here.
For dev mode, `python -m synapse` → __main__.py is still the way to run."""
from synapse.app import main

if __name__ == "__main__":
    raise SystemExit(main())
