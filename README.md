<div align="center">

<img src="assets/icon.png" width="96" alt="PsychoNotes icon">

# PsychoNotes

**A private, offline workspace for practicing psychologists: client records, session notes and progress tracking.**

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Kivy](https://img.shields.io/badge/Kivy-2.3-6aa58e)
![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-lightgrey)
![Offline](https://img.shields.io/badge/data-100%25%20offline-2c6a58)
![License](https://img.shields.io/badge/license-MIT-green)

<img src="docs/screenshots/home.jpg" width="24%" alt="Home: next appointment, stats, sessions to complete">
<img src="docs/screenshots/client.jpg" width="24%" alt="Client card with progress chart">
<img src="docs/screenshots/session.jpg" width="24%" alt="Session details">
<img src="docs/screenshots/history.jpg" width="24%" alt="Session history">

</div>

---

Paper notes get lost, and spreadsheets don't fit how therapy works. PsychoNotes keeps each client's profile, every session and the client's state over time in one place. Nothing leaves the device: there's no account, no cloud and no network access.

The interface is in Russian, because the app was built for Russian-speaking practitioners.

## Features

### What matters most comes first
- **The next appointment** is the hero card on the home screen. It shows a countdown and opens that session's notes in one tap.
- **"Нужно заполнить" ("Needs completing")** lists past sessions still missing an outcome or a final score, so no write-up gets forgotten.
- An unfinished session shows a reminder banner. Leaving a form with unsaved edits asks before discarding them.

### Clients and sessions
- **Client profile:** age, phone, temperament, perception modality, character type, anamnesis and help plan.
- **Requests:** a client can have any number of presenting requests. They come back as one-tap suggestions when you record a session.
- **Session form** in four steps: meeting, at the start, the work, the outcome.
- **State scores:** rated 0–10 at the start and at the end, on a colour-coded scale from "плохо" (bad) to "отлично" (excellent).
- **Quick input:** a date picker, chips for place and weather, and client selection from a list. A new client can be created right there.
- **Search** is instant and case-insensitive, Cyrillic included. It covers clients, requests and techniques.

### Progress
- **Per-client chart** of the before and after scores across sessions. Tap or hover a point for its values.
- **Plain-language summary** under the chart, such as "Состояние после сессий выросло с 4 до 7" ("The state after sessions rose from 4 to 7").
- **Per-session change** ("+3") is shown on every session.

### Your data
- **JSON backup and restore.** A restore validates the file first and rolls back completely if anything is wrong.
- **CSV export** of all sessions. It opens in Excel with Cyrillic intact.
- **Light and dark themes** in soft pastels with matte, frosted panels.
- **Demo data:** one tap loads a few fictional clients to explore the app with.

<table>
<tr>
<td align="center" width="25%"><img src="docs/screenshots/session_form.jpg" alt="Session form"><br><sub>Four-step session form</sub></td>
<td align="center" width="25%"><img src="docs/screenshots/session_todo.jpg" alt="Unfinished session"><br><sub>Unfinished session reminder</sub></td>
<td align="center" width="25%"><img src="docs/screenshots/clients.jpg" alt="Clients"><br><sub>Clients</sub></td>
<td align="center" width="25%"><img src="docs/screenshots/settings_dark.jpg" alt="Settings, dark theme"><br><sub>Backups and themes</sub></td>
</tr>
</table>

### Dark theme

<p align="center">
<img src="docs/screenshots/home_dark.jpg" width="30%" alt="Home, dark theme">
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

On first launch, tap **"Посмотреть на демо-данных"** ("View demo data") to load a few fictional clients.

The database lives in the OS user-data folder, for example `~/Library/Application Support/psychonotes/` on macOS or `%APPDATA%\psychonotes\` on Windows. Backups are saved to `~/Documents/PsychoNotes`. On Android they go to the app's own folder, which file managers can see.

### Packaging

| Target | Command |
|---|---|
| Android APK | `buildozer android debug` (config in `buildozer.spec`). Builds for arm64-v8a and armeabi-v7a, with a minimum of Android 7.0. The first build takes about 30 min; later ones take about a minute. See [CLAUDE.md](CLAUDE.md#android-build-buildozer) for macOS notes and two python-for-android workarounds. |
| Windows / macOS app | `pyinstaller --name PsychoNotes --windowed --icon assets/icon.png --add-data "ui.kv:." --add-data "assets:assets" main.py` (on Windows, use `;` instead of `:`) |

## Under the hood

| | |
|---|---|
| **UI** | Kivy 2.3 with every layout in a single `ui.kv`. No KivyMD and no third-party widgets. |
| **Icons** | Material Icons Round, cut down to the 32 glyphs the app uses: **5 KB** instead of 400 KB. |
| **Storage** | SQLite (stdlib) with foreign-key cascades, indexes and a Unicode-aware `casefold()` SQL function for search. |
| **Lists** | `RecycleView` for clients and history, so only the rows on screen exist. |
| **Glass effect** | A translucent fill, a 1:1 grain texture and a soft highlight on a GPU `BoxShadow`. No real-time blur and no per-frame FBOs. |
| **Startup** | Only the home screen is built at launch. Other screens are created on first visit. |

Measured on an M-series Mac with a stress database of 300 clients and 6,000 sessions:

| Metric | Result |
|---|---|
| Launch to first frame | ~0.5 s |
| Scrolling the 6,000-row history | steady 13 ms/frame (vsync-bound) |
| Heaviest query (all sessions) | ~22 ms |
| Memory above a bare Kivy window | +36 MB |
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

The unit tests run on any Python 3.9+ with nothing to install. The smoke test opens a window and walks through the main flows:
- creating a client and a session through the pickers;
- the unsaved-changes prompt and rejection of invalid input;
- deletion, and backup and restore;
- a real touch on a button, routed through Kivy's input loop.

The screenshots in this README are generated by `tools/screenshots.py`.

## Privacy

- All data stays in a local SQLite file. The app makes no network requests.
- Android backup to Google's cloud is turned off (`android.allow_backup = False`).
- Treat backup files like the records they contain: they are plain JSON.

## Upgrading from 1.x

The database schema is unchanged. On first start, 2.0 copies an existing `psychologist_notes.db` from the app folder into the user-data folder. Version 2.0 also fixes several 1.x bugs:
- Editing a session no longer wipes the client's anamnesis and requests.
- Deleting a client now also removes their sessions.
- A session is linked to a client picked from a list rather than a typed name, so typos no longer create duplicate clients.

## License

[MIT](LICENSE) © Efim Romanchenko

Icons: [Material Icons](https://github.com/google/material-design-icons) by Google, Apache License 2.0 (subset in `assets/icons.otf`).
