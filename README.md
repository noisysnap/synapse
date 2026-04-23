# Synapse

A lightweight Windows 11 translator that lives in the system tray. Select
text anywhere, press **Ctrl + C + C** (Ctrl held, double-tap C), and a
translation pops up next to the cursor. Direction is detected
automatically across 20+ languages. Translations stream in word by word —
the first token usually appears in well under a second.

Two providers are supported: **OpenRouter** or
**Anthropic API**. The default model
is Claude Haiku 4.5.

![icon](icon.png)

## Features

- Global hotkey: hold `Ctrl`, double-tap `C` — translation appears at the
  cursor. A single `Ctrl+C` still works as a normal copy.
- Streaming responses — the popup fills in as the model writes.
- Auto-detects 21 source languages (Cyrillic split into ru/uk, Latin via
  diacritics + stop-word scoring, CJK/Arabic/Hindi by script).
- Standalone editor window (Google-Translate style) with debounced
  auto-translate, language swap, and Ctrl+Enter for instant translate.
- API keys stored in **Windows Credential Manager** via the `keyring`
  package. Keys never touch disk.
- Custom prompt slot for tone/style hints, with prompt-injection
  sanitisation.
- Optional close-on-copy and "paste to source window" behaviours.
- UI translated into Russian, English, Japanese, Spanish, Portuguese.
- Optional autostart with self-healing path (move the build folder, the
  registry entry rewrites itself).
- Single-file PyInstaller build (`onedir`).

## Requirements

- Windows 10/11 (development is on Windows 11; other platforms are not
  tested)
- Python 3.11+

## Install (dev mode)

```bat
git clone https://github.com/<you>/synapse.git
cd synapse
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Get an API key

Two providers are supported. Switch between them in **Settings**.

**OpenRouter**:

1. Open https://openrouter.ai/keys
2. Create a key (starts with `sk-or-v1-…`).
3. Save it via `python -m synapse.setup_key` or in the **Settings** dialog.

**Anthropic direct**:

1. Open https://console.anthropic.com/settings/keys
2. Create a key (starts with `sk-ant-…`).
3. In **Settings**, switch to the **Anthropic** tab, paste, save.

Keys are stored in Windows Credential Manager (service `synapse`, users
`openrouter_api_key` and `anthropic_api_key`) via the `keyring` package.
The active provider is held in `active_provider` in `config.json` and
synced with the selected tab on save.

## Run

```bat
python -m synapse
```

No window opens — a "T" tray icon should light up. Right-click for the
menu, double-click for the editor.

## How the trigger works

- Hold and keep holding `Ctrl`.
- Quickly tap `C` twice (the second press within ~400 ms of the first).
- The first `Ctrl+C` copies the selection as usual.
- The second `C` (with `Ctrl` still held) opens the popup.

If `Ctrl` is released between the two `C` presses, it's just two normal
`Ctrl+C` operations — no trigger. Holding `C` (autorepeat) does not
count.

The popup:

- Closes on `Esc` or click outside.
- Replaces its content on a new trigger (does not stack windows).
- Has **Copy** and **Paste** buttons.
- Lets you change source/destination languages inline (re-translates
  without flashing the loading state).

## Tray menu

- **Pause / Resume** — turn the keyboard listener on/off.
- **Editor** — open the standalone translation editor.
- **Settings…** — provider, model, key, languages, autostart,
  close-on-copy.
- **Exit** — quit the application.
- Double-click the icon to open the editor.

## Configuration

`config.json` lives next to the package (next to `Synapse.exe` in a
build). Created on first save — defaults are baked into
`synapse/config.py`. Example:

```json
{
  "active_provider": "anthropic",
  "custom_prompt": "",
  "preferred_dst_lang": "en",
  "ui_lang": "en",
  "openrouter": {
    "model": "anthropic/claude-haiku-4.5",
    "base_url": "https://openrouter.ai/api/v1"
  },
  "anthropic": {
    "model": "claude-haiku-4-5"
  },
  "trigger": { "double_c_window_ms": 400 },
  "popup": {
    "default_width": 480,
    "default_height": 280,
    "cursor_offset_x": 16,
    "cursor_offset_y": 16,
    "close_on_copy": false
  },
  "editor": {
    "width": 900,
    "height": 520,
    "debounce_ms": 500
  }
}
```

`active_provider` — `"openrouter"` or `"anthropic"`.

## Debug logs

```bat
set SYNAPSE_DEBUG=1
python -m synapse
```

Logs are written to stderr only.

## Autostart

In **Settings → System** there is a checkbox **Launch on Windows
startup**. It writes to
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`: in dev mode the
command is `pythonw -m synapse`; in a build it is the path to
`Synapse.exe`. If the build folder is moved, the next manual launch
self-heals the registry entry.

## Build a `.exe`

The build uses PyInstaller in `--onedir` mode (a folder containing
`Synapse.exe` plus dependencies).

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install pyinstaller
pyinstaller Synapse.spec
```

cmd:

```bat
.venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller Synapse.spec
```

Result: `dist\Synapse\Synapse.exe`. The folder is fully relocatable.
`config.json` is created next to the exe on first save. Keys stay in
Windows Credential Manager — they are not bound to the exe.

## Manual acceptance checklist

Run through this before tagging a release:

- [ ] `python -m synapse` → tray icon appears, no windows.
- [ ] Select Russian text in any app → `Ctrl + C + C` → English
      translation appears at the cursor within ~1 s.
- [ ] Same with English text → Russian translation.
- [ ] A single `Ctrl+C` copies as usual, no popup, no delay.
- [ ] `Esc` closes the popup.
- [ ] A new trigger on different text replaces the popup content (does
      not open a second window).
- [ ] **Pause** in the tray disables the trigger; **Resume** brings it
      back.
- [ ] **Exit** fully terminates the process (icon disappears, the python
      process exits).
- [ ] Empty clipboard on trigger → nothing happens.
- [ ] Missing/invalid key → clear message in the popup and an offer to
      enter a key in **Settings**.

## Project layout

```
synapse/
├── __init__.py
├── __main__.py            # python -m synapse entry
├── app.py                 # SynapseApp — wires UI, signals, providers
├── autostart.py           # HKCU\…\Run integration
├── config.py              # config.json load/save
├── editor.py              # standalone editor window
├── i18n.py                # in-memory translations for the UI
├── lang.py                # language detection (script + diacritics + stop-words)
├── lang_picker.py         # language combobox widget
├── popup.py               # cursor-anchored translation popup
├── setup_key.py           # CLI: python -m synapse.setup_key
├── tray.py                # tray icon, menu, settings dialog
├── trigger.py             # double-Ctrl-C keyboard listener
├── assets/
│   └── icon.ico
└── providers/
    ├── __init__.py
    ├── base.py            # system prompt, sanitisation, refusal detection
    ├── keys.py            # Credential Manager wrappers
    ├── openrouter.py      # OpenRouter (OpenAI-compatible) translator
    └── anthropic_direct.py # Anthropic SDK translator
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

PRs and issues are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the basics.

## Out of scope (v1)

Manual direction override; translation history; offline mode; macOS or
Linux support.
