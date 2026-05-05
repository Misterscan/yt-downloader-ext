# YT Downloader

A browser extension + local backend that lets you download YouTube videos and playlists directly from your browser as **MP3** or **MP4**.

## How It Works

- A **Chrome/Edge extension** (Manifest V3) provides a popup UI for the current YouTube tab.
- A **Flask backend** (`app.py`) runs locally on `http://localhost:5001`, handling downloads via `yt-dlp` and post-processing via `ffmpeg`.
- The extension communicates with the backend over HTTP. Downloaded files are saved to the `downloads/` folder.

## Features

- Download single videos or full playlists
- Output formats: **MP3** (audio) or **MP4** (video)
- MP3 quality: 128 / 192 / 320 kbps
- MP4 quality: up to 1080p / 720p / 480p / 360p
- Playlist downloads run as background jobs with progress tracking
- MP3 files get embedded cover art (square-cropped thumbnail) and metadata
- Custom title and artist override before downloading

## Requirements

- Python 3.10+
- `ffmpeg` on PATH (or set `FFMPEG_LOCATION` env var)
- Google Chrome or Microsoft Edge

## Setup

### 1. Install Python dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install flask flask-cors yt-dlp
```

### 2. Install the backend as a scheduled task (Windows)

Runs the Flask server automatically at login:

```powershell
.\scripts\install-helper.ps1
```

To check status:

```powershell
.\scripts\status-helper.ps1
```

To uninstall:

```powershell
.\scripts\uninstall-helper.ps1
```

To start manually without installing:

```powershell
.\scripts\start-helper.ps1
```

### 3. Load the browser extension

1. Open Chrome/Edge and go to `chrome://extensions` (or `edge://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** and select this project folder.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/info?url=<url>` | Fetch video/playlist metadata |
| `GET/POST` | `/download` | Download a single video |
| `POST` | `/playlist-download` | Start an async playlist download job |
| `GET` | `/playlist-status/<job_id>` | Poll playlist job progress |
| `GET` | `/file/<filename>` | Retrieve a downloaded file |

## Project Structure

```
app.py               # Flask backend
manifest.json        # Chrome extension manifest (v3)
popup.html           # Extension popup UI
popup.js             # Extension popup logic
downloads/           # Output folder for downloaded files
logs/                # Backend stdout/stderr logs
scripts/
  install-helper.ps1    # Register Windows scheduled task
  start-helper.ps1      # Start backend manually
  status-helper.ps1     # Check scheduled task status
  uninstall-helper.ps1  # Remove scheduled task
  install-helper.sh     # macOS: install launchd service
  uninstall-helper.sh   # macOS: remove launchd service
  com.(root_folder).ytdownload-helper.plist  # macOS launchd plist
```

## macOS

Use the shell scripts for launchd-based auto-start:

```bash
bash scripts/install-helper.sh
bash scripts/uninstall-helper.sh
```

Set `FFMPEG_LOCATION` if `ffmpeg` is not on your PATH (e.g., Homebrew on Apple Silicon defaults to `/opt/homebrew/bin`).

## Notes

- The backend must be running before using the extension.
- Files are saved in the `downloads/` folder next to `app.py`.
- Duplicate filenames are automatically numbered (e.g., `Song (2).mp3`).
