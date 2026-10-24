# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

PsychoNotes is an offline Kivy app for psychologists: client profiles, session notes, and 0–10 state-score tracking in local SQLite. It targets desktop and Android (Buildozer). The UI text is Russian; code and comments are English.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # only dependency: kivy
.venv/bin/python main.py                  # run (real DB in the OS user-data dir)
PSYCHONOTES_DB=/tmp/x.db .venv/bin/python main.py   # run against a throwaway DB
python -m unittest                        # all tests; no Kivy needed
python -m unittest test_database.DatabaseTest.test_delete_client_cascades   # one test
.venv/bin/python tools/smoke.py                    # GUI smoke test of the main flows (exit 0/1); run after UI changes
.venv/bin/python tools/screenshots.py [out_dir]     # drive every screen on demo data, save PNGs
```

## Android build (Buildozer)

`buildozer android debug` produces `bin/psychonotes-<ver>-arm64-v8a_armeabi-v7a-debug.apk`. The first build compiles CPython, SDL2, OpenSSL and Kivy for both ABIs (about 30 min) and downloads the SDK/NDK into `~/.buildozer`. Later builds reuse `.buildozer/` and take about a minute. On macOS it needs `openjdk@21` as `JAVA_HOME`, GNU `libtool` first in `PATH` (`/opt/homebrew/opt/libtool/libexec/gnubin`), and buildozer run from a venv with `VIRTUAL_ENV` set, or buildozer tries `pip install --user`.

The python-for-android master checked out under `.buildozer/android/platform/python-for-android` has two bugs that break this build. After a fresh clone, patch both and rebuild:
- `pythonforandroid/recipes/kivy/__init__.py`: set `python_depends = ['filetype']`. `requests` pulls in an Android-only `charset_normalizer` wheel that the host pip then refuses to install. The app makes no network requests, so nothing is lost.
- `pythonforandroid/build.py` in `run_pymodules_install`: use `'-m', 'venv', '--clear', 'venv'`. Without `--clear`, the venv is recreated over the previous ABI's venv, two pip versions get mixed, and pip fails with `ImportError: BuildDependencyInstallError`.

Harmless log noise: `Traceback` blocks from `pip install ... --dry-run` mean only that no prebuilt Android wheel exists, and the recipe then builds from source. `JDK version 21 is not supported` is also only a warning.

Test on the emulator: `adb install -r bin/*.apk`, then `adb logcat -s python`. `adb shell input tap` is sometimes missed by SDL; `input swipe x y x y 150` taps reliably.

README screenshots are compact JPEGs: `sips -s format jpeg -s formatOptions 82 --resampleWidth 600 x.png --out docs/screenshots/x.jpg`. The PNGs are about 1 MB each because of the grain texture.

## Architecture

- `database.py`: pure stdlib, no Kivy. `Database(path)` holds one connection with `PRAGMA foreign_keys = ON`, returns rows as dicts, and registers a `casefold()` SQL function, because SQLite's `LIKE`/`lower()` only fold ASCII and Cyrillic search would break. `CLIENT_FIELDS`/`NOTE_FIELDS` drive the INSERT/UPDATE SQL. The schema matches v1 on purpose, so old databases open unchanged; do not alter it without a migration. `dashboard()` splits sessions into upcoming, todo (past and missing a final score or outcome) and recent.
- `main.py`: app, navigation and all screens. `THEMES` holds the colour tokens (8-digit hex = RGBA). Every key must also appear in the `ColorProperty` tuple on `PsychoNotesApp`, with the count in `range(N)` kept in sync. `ui.kv` reads them as `app.<token>`, so a theme switch is just property assignment.
- `ui.kv`: every layout and style, loaded explicitly via `Builder.load_file` (not auto-loaded). `Glass` is the base panel (shadow, translucent fill, grain, sheen, rim). Its style is in kv, but the class lives in `main.py`; `Card`, `RowBase`, `StatTile`, `NavBar` and `ModalCard` extend it.
- `fmt.py`: Russian dates, plurals and relative times. `demo.py`: fictional seed data.

### Navigation

`app.go(name, **kw)` / `app.back()`, never `sm.current = ...` directly.
- Tabs (`TABS`) clear the stack and use `NoTransition`. Other screens push `(name, kw)` onto `app.stack`.
- The target screen gets `screen.kw = kw`, and `Page.on_pre_enter` calls `refresh()`, which reloads from the DB. Returning via back therefore shows fresh data.
- Only `home` is declared in kv. The other screens are created on first visit from the `SCREENS` map. A new screen needs both a `Page` subclass and a `SCREENS` entry.
- `FormPage` screens implement `collect()` and call `mark_clean()` at the end of `refresh()`. `back()` asks for confirmation if `collect()` changed, so code paths that save or delete must call `back(force=True)`.

## Kivy gotchas hit in this codebase

- Properties declared in kv on dynamic classes (`<Foo@Label>: active: False`) can't be passed as `__init__` kwargs. Create them with `make('Foo', active=True)`.
- Those properties are still `None` while `canvas.before` is first built, so canvas expressions use `self.bg or (0, 0, 0, 0)`.
- A property named `on_<x>` is treated as the event handler for `<x>`. That is why the theme token is `accent_fg`/`ink`, not `on_accent`.
- `TextInput` draws its text with the last `Color` in `canvas.before`. A custom `Field` background must end by restoring the text colour, or the text becomes invisible.
- The first screen gets `on_pre_enter` before its kv rule has been applied, hence the `if self.children:` guard. Don't guard on `ids`: a rule without any `id` would then never refresh. `on_start` refreshes home explicitly.
- `RoundedRectangle` doesn't tile textures. The grain uses `texture.get_region()` sized 1:1 to the widget.
- `Window.screenshot()` reads the GL back buffer at an arbitrary moment and returns stale or overlapping frames. Use `widget.export_to_png()`, as `tools/screenshots.py` does.
- Widgets are hidden by setting `height: 0`, `opacity: 0` and `disabled: True`. Their children are still laid out past the zero-height box, and a disabled widget swallows any touch that collides with it, so it blocks taps on whatever lies underneath. `Glass.on_touch_down` ignores touches while `height == 0`; put any new hideable container on `Glass`, or guard it the same way.
- `tools/smoke.py` mostly calls methods directly. Hit-testing bugs only show up under real input, so use its `Tap(x, y)()` helper, which goes through `EventLoop`, for those. `kivy.tests` needs pytest, so it isn't used.
- `FadeTransition` (FBO-based) produced black frames in the dark theme. Tabs use `NoTransition`.

## Conventions

- Score colours (`score_low/mid/high`) and chart series colours are separate tokens. The chart's orange/blue pair was validated for colour-blind separation; don't swap it for pastels.
- Pastel fills (`accent_fill`, scores, `tint1-4` avatars) always carry `ink` text.
- `assets/icons.otf` is a subset of Material Icons Round. To add an icon, re-run `pyftsubset` on the full font with the new codepoint added, then add the name to the `I` dict in `ui.kv`.
