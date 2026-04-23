# Contributing to Synapse

Thanks for considering a contribution. The project is small and Windows-only,
so the bar is light: working code, no surprises.

## Local setup

```bat
git clone https://github.com/<you>/synapse.git
cd synapse
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run from source:

```bat
python -m synapse
```

Set `SYNAPSE_DEBUG=1` for stderr logs.

## Making changes

- Match the existing style: type hints, `from __future__ import annotations`,
  short comments only when the **why** is non-obvious.
- All comments and docstrings in English.
- User-facing strings go through `synapse/i18n.py` (`t("key")`). Add the
  English copy first, then translations for the other supported UI languages
  if you can — otherwise leave the existing copy and open an issue.
- Keep the dependency list tight. New runtime deps need a justification in the
  PR description.

## Testing

There is no automated test suite yet. Before opening a PR, walk through the
**Manual acceptance checklist** in the README, especially:

- Trigger fires on `Ctrl + C + C`, single `Ctrl + C` is unaffected.
- Popup appears at the cursor and streams text in.
- Pause / Resume in the tray actually disables / enables the listener.
- A bad/missing API key produces a readable message, not a stack trace.

## Pull request checklist

- [ ] Code runs (`python -m synapse`) without console errors.
- [ ] No Russian (or other non-English) text in comments or docstrings.
- [ ] New user-facing strings are routed through `t(...)`.
- [ ] If you touched `Synapse.spec`, `pyinstaller Synapse.spec` still produces
      a working `dist\Synapse\Synapse.exe`.
- [ ] PR description explains the **why**, not just the **what**.

## Issues

Bug reports: include Windows version, Python version (or "build"), and the
relevant section of `SYNAPSE_DEBUG=1` output. Screenshots help for UI bugs.

Feature requests: state the use case before the proposed solution. The current
scope is intentionally narrow (see README's "Out of scope" section).
