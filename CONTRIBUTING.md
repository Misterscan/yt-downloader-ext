# Contributing to YT Downloader

Thank you for taking the time to contribute! This document covers how to set up a development environment, coding conventions, and the pull request process.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Issues](#reporting-issues)

---

## Development Setup

### Requirements

- Python 3.9+
- FFmpeg
- Google Chrome

### Backend

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run the server in debug mode
python backend/app.py
```

The server starts at `http://127.0.0.1:5001`. You can test endpoints directly with `curl`:

```bash
curl "http://127.0.0.1:5001/health"
curl "http://127.0.0.1:5001/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Extension

1. Open `chrome://extensions/` in Chrome
2. Enable **Developer mode**
3. Click **Load unpacked** and select the `extension/` folder
4. After any change to `popup.js` or `popup.html`, click the **reload** icon on the extension card

---

## Project Structure

```
backend/app.py      — Flask routes, yt-dlp integration, FFmpeg post-processing
extension/popup.js  — All extension UI logic and backend communication
extension/popup.html — Extension popup markup and styles
```

---

## Making Changes

### Backend (`backend/app.py`)

- New routes should follow the existing pattern: validate input, call yt-dlp/FFmpeg, handle errors, return JSON.
- Keep `build_ydl_opts()` and `embed_mp3_artwork()` as the central helpers for media options and tagging — extend them rather than duplicating logic.
- Playlist jobs are tracked in the in-memory `playlist_jobs` dict. If you add persistent state, document the tradeoffs.
- FFmpeg is resolved via `resolve_ffmpeg_location()` — do not hardcode paths.

### Extension (`extension/popup.js`)

- All backend calls go through `fetch()` against `http://127.0.0.1:5001`.
- Progress polling for playlists uses `setInterval` — make sure to clear it (`clearInterval`) on completion or error.
- Keep UI state changes (button labels, progress bar) close to the fetch call they correspond to for readability.

### Adding a dependency

- Python: add it to `backend/requirements.txt`
- Extension: keep it dependency-free (vanilla JS only) unless there's a strong reason

---

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use descriptive variable names; avoid single-letter names outside of loop indices
- Add a docstring to any new function
- Handle exceptions at the call site; avoid bare `except:` clauses

### JavaScript

- Use `const` / `let` — never `var`
- Prefer `async/await` over raw `.then()` chains
- Keep DOM queries at the top of functions or cached in variables
- No external libraries or `import` statements (Manifest V3 popup context)

---

## Submitting a Pull Request

1. **Fork** the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** following the guidelines above.

3. **Test manually:**
   - Single video MP3 download
   - Single video MP4 download
   - Playlist download (progress bar + ZIP delivery)
   - Edge cases: private videos, live streams, age-restricted content

4. **Commit** with a clear message:
   ```
   feat: add support for audio-only WAV export
   fix: resolve crash when playlist has deleted entries
   docs: update API reference for /playlist/start
   ```
   Use the [Conventional Commits](https://www.conventionalcommits.org/) format.

5. **Open a Pull Request** against `main`. Include:
   - What the change does and why
   - Steps to reproduce any bug being fixed
   - Screenshots or logs if relevant

---

## Reporting Issues

Please open a [GitHub Issue](../../issues) and include:

- **OS version** and **Chrome version**
- **Python / yt-dlp version** (`python3 --version`, `yt-dlp --version`)
- The **YouTube URL** that caused the problem (if shareable)
- The **error message** from the extension popup and/or from the backend log.

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
