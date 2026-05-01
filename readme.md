# EXFO Job Manager

A Flask-based web application for managing EXFO PXM jobs, assigning jobs to connected devices, and generating structured job folders from Excel data.

This repository is intended to be portable: another developer can clone it, install dependencies, and run the app without uploading large local data folders.

## Quick Guide

### What to include in GitHub

Keep the repository focused on source code and configuration.

Include:
- `app.py`
- `config.py`
- `main.py`
- `README.md`
- `members.json`
- `pxms.json`
- `.gitignore`
- `services/`
- `utils/`
- `templates/`
- `static/`
- `routes/` (if used by the current application)

Do not include:
- `.venv/`
- `__pycache__/`
- `.vscode/`
- `data/`
- `jobs/`
- `uploads/`
- `pxm_jobs/`
- `*.db`

Those directories are local runtime artifacts and may contain large or machine-specific files.

## Prerequisites

- Python 3.10+ installed
- A virtual environment for dependency isolation
- `pip` available

## Install dependencies

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install Flask pandas openpyxl
```

If you want, add a `requirements.txt` file later with:

```bash
pip freeze > requirements.txt
```

## Running the app

From the project directory:

```bash
.venv\Scripts\activate
python app.py
```

Then open the browser at:

```
http://127.0.0.1:9443
```

## How device detection works

The app detects a connected PXM device by checking mounted Windows drives.

- Known devices are stored in `pxms.json`
- Each device usually has a `drive` field like `E:` or `I:`.
- The app checks whether that drive exists and whether it contains a `Jobs` folder.

If the device is mounted with a different letter on another computer, the app can still work if the drive is re-registered or the current drive is detected.

## Important notes for collaborators

- Do not commit local data folders or generated databases.
- The app can recreate missing directories like `jobs/` automatically.
- A cloned copy of this repo should work on another PC once dependencies are installed.

## How to use the app

- `/jobs` — browse available jobs and assign them to a connected PXM
- `/exfo` — manage connected EXFO devices and serials
- `/devices` — register devices, assign users, and view device status
- `/assigned` — view jobs currently loaded on a connected PXM

## Project structure

- `app.py` — Flask server and routes
- `config.py` — path and service imports
- `services/` — device registry, history, and path helpers
- `utils/` — job loading, DB import, data helpers
- `templates/` — HTML templates
- `static/` — CSS and JavaScript assets

---

If this repo is cloned to another machine, that machine just needs Python and the listed dependencies. The app will create the missing local folders on startup.