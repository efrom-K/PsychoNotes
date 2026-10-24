<div align="center">

<img src="assets/icon.png" width="96" alt="PsychoNotes icon">

# PsychoNotes

**A private, offline workspace for practicing psychologists: client records, session notes and progress tracking.**

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Kivy](https://img.shields.io/badge/Kivy-2.3-6aa58e)
![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

<img src="docs/screenshots/home.jpg" width="24%" alt="Home"> <img src="docs/screenshots/client.jpg" width="24%" alt="Client card"> <img src="docs/screenshots/session_form.jpg" width="24%" alt="Session form"> <img src="docs/screenshots/home_dark.jpg" width="24%" alt="Dark theme">

</div>

---

Paper notes get lost, and spreadsheets don't fit how therapy works. PsychoNotes keeps each client's profile, every session and the client's state over time in one place. Nothing leaves the device: no account, no cloud, no network access.

The interface is in Russian, because the app was built for Russian-speaking practitioners.

## Features

**The things that matter most come first**
- **Next appointment** is the hero card on the home screen, with a countdown and a one-tap way to open its notes.
- **"Needs completing"** lists past sessions that still lack an outcome or a final score, so no write-up gets forgotten.
- An unfinished session shows a reminder banner, and leaving a form with unsaved edits asks before discarding them.

**Clients**
- Profile: age, phone, temperament, perception modality, character type, anamnesis and help plan.
- Any number of presenting requests. They become one-tap suggestions when you record a session.
- Instant search, case-insensitive including Cyrillic.

**Sessions**
- A four-step form: meeting, at the start, the work, the outcome.
- State scored 0–10 at the start and end on a colour-coded scale from "плохо" (bad) to "отлично" (excellent).
- A date picker, quick chips for place and weather, and client selection from a list, with the option to create a client right there.

**Progress**
- Per-client chart of the before and after scores across sessions (tap or hover for values), plus a plain-language summary such as "Состояние после сессий выросло с 4 до 7" ("The state after sessions rose from 4 to 7").
- Every session shows its change ("+3") at a glance.

**Your data**
- JSON backup and restore. A restore validates the file first and rolls back completely if anything is wrong.
- CSV export of all sessions, readable by Excel including Cyrillic.
- Light and dark themes in soft pastels with matte, frosted panels.
- Demo data, so the app can be explored in a click.

<p align="center">
<img src="docs/screenshots/session_todo.jpg" width="30%" alt="Unfinished session reminder">
<img src="docs/screenshots/client_dark.jpg" width="30%" alt="Client card, dark theme">
</p>

## Getting started

```bash
git clone https://github.com/efrom-K/PsychoNotes.git
cd PsychoNotes
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

On first launch, choose **"Посмотреть на демо-данных"** ("View demo data") to load a few fictional clients.

The database lives in the OS user-data folder, for example `~/Library/Application Support/psychonotes/` on macOS or `%APPDATA%\psychonotes\` on Windows. Backups go to `~/Documents/PsychoNotes`.

### Packaging

| Target | Command |
|---|---|
| Android APK | `buildozer android debug` (config in `buildozer.spec`, Linux/WSL) |
| Windows / macOS app | `pyinstaller --name PsychoNotes --windowed --icon assets/icon.png --add-data "ui.kv:." --add-data "assets:assets" main.py` (on Windows use `;` instead of `:`) |

## Under the hood

| | |
|---|---|
| **UI** | Kivy 2.3 with all layout in a single `ui.kv`. No KivyMD and no third-party widgets. |
| **Icons** | Material Icons Round, cut down to the 32 glyphs the app uses: **5 KB** instead of 400 KB. |
| **Storage** | SQLite (stdlib) with foreign-key cascades, indexes and a Unicode-aware `casefold()` SQL function for search. |
| **Lists** | `RecycleView` for clients and history, so only the rows on screen exist. |
| **Glass effect** | Translucent fill, 1:1 grain texture and a soft highlight on GPU `BoxShadow`. No real-time blur and no per-frame FBOs. |
| **Startup** | Only the home screen is built at launch. Other screens are created on first visit. |

Measured on an M-series Mac with a stress database of 300 clients and 6,000 sessions:

| Metric | Result |
|---|---|
| Launch to first frame | ~0.5 s |
| Scrolling 6,000-row history | steady 13 ms/frame (vsync-bound), max 13.3 ms |
| Heaviest query (all sessions) | ~22 ms |
| Memory over a bare Kivy window | +36 MB |
| App source + assets | ~140 KB |

```
main.py          app shell, navigation, screens, chart widget
ui.kv            every layout and style; colour tokens come from the theme in main.py
database.py      SQLite layer, pure stdlib (no Kivy), with backup/restore and CSV
fmt.py           Russian dates, plurals, "in 2 h 15 min"
demo.py          fictional sample data
test_database.py unit tests for the data layer and formatting
tools/           GUI smoke test, screenshot generator for this README
```

## Tests

```bash
python -m unittest                  # data layer and formatting, no Kivy needed
.venv/bin/python tools/smoke.py     # GUI smoke test: drives real flows in a live window
```

The unit tests run on any Python 3.9+ without installing anything. The smoke test opens a window and walks through the main flows: creating a client and a session through the pickers, the unsaved-changes prompt, invalid input, deletion and backup/restore.

## Privacy

- All data stays in a local SQLite file. The app makes no network requests.
- Android backup to Google's cloud is disabled (`android.allow_backup = False`).
- Treat backup files like the records they contain: they are plain JSON.

## Upgrading from 1.x

The database schema is unchanged. On first start, 2.0 copies an existing `psychologist_notes.db` from the app folder into the user-data folder. Version 2.0 also fixes several 1.x bugs:
- Editing a session no longer wipes the client's anamnesis and requests.
- Deleting a client now also removes their sessions.
- A session is linked to a client picked from a list rather than to a typed name, so typos no longer create duplicate clients.

## License

[MIT](LICENSE) © Efim Romanchenko

Icons: [Material Icons](https://github.com/google/material-design-icons) by Google, Apache License 2.0 (subset in `assets/icons.otf`).
