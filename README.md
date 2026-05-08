<h1 align="center">🚀 YT Downloader</h1>

<p align="center">
  <img src="extension/logo.png" width="200" alt="YT Downloader Logo">
</p>

<div align="center">

[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Local-orange.svg?style=for-the-badge)]()
[![Platforms](https://img.shields.io/badge/Platforms-Mac|Windows|Linux-blue.svg?style=for-the-badge)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

A high-performance **Chrome extension** and **Python backend** suite designed for seamless YouTube media extraction. Download videos and playlists directly to your local storage with automated metadata tagging and high-fidelity quality control.

> [!IMPORTANT]
> **For personal use only.** Please respect YouTube's [Terms of Service](https://www.youtube.com/t/terms) and only download content you have the right to access.

---

## ✨ Core Features

| Feature                 | Description                                                              |
| :---------------------- | :----------------------------------------------------------------------- |
| 🎵 **Audio Mastering**  | MP3 export with selectable bitrates (128k, 192k, 320k).                  |
| 🎬 **Video Quality**    | MP4 support from 720p up to **4K Ultra HD**.                             |
| 🖼️ **Smart Tagging**    | Automatic ID3 metadata injection and square-cropped cover art embedding. |
| 📋 **Batch Processing** | Full playlist support with asynchronous downloading and ZIP archiving.   |
| ✏️ **Manual Overrides** | Direct control over Title and Artist fields before processing starts.    |

---

## 🛠️ System Requirements

| Requirement      | Command to Install         |
| :--------------- | :------------------------- |
| **Python 3.14+** | `brew install python@3.14` |
| **FFmpeg 8.0**   | `brew install ffmpeg@8`    |

---

## 🚀 Quick Start

### 1. Repository Setup

```bash
git clone https://github.com/Misterscan/download-yt.git
cd download-yt
```

### 2. Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. Chrome Extension

1. Navigate to `chrome://extensions/` in Chrome.
2. Enable **Developer mode** (top-right).
3. Click **Load unpacked** and select the `extension/` directory.

---

## 💻 Architecture Overview

The system operates as a client-server architecture localized to your machine for maximum privacy and speed:

- **Frontend**: A Chrome Extension (Manifest V3) providing a dynamic UI and YouTube page integration.
- **Backend**: A Flask-based Python API leveraging `yt-dlp` and `FFmpeg` for media processing.
- **Persistence**: Managed via local server execution.

```mermaid
graph TD
    A[Chrome Extension] -->|REST API| B[Flask Backend :5001]
    B --> C[yt-dlp]
    B --> D[FFmpeg]
    C -->|Fetch| E[YouTube]
    D -->|Process| F[Local Storage]
```

---

## 📡 API Endpoints

| Method | Endpoint               | Purpose                           |
| :----- | :--------------------- | :-------------------------------- |
| `GET`  | `/health`              | Verify server connectivity.       |
| `GET`  | `/info`                | Retrieve video/playlist metadata. |
| `POST` | `/download`            | Trigger single-item download.     |
| `POST` | `/playlist/start`      | Initialize async playlist job.    |
| `GET`  | `/playlist/status/:id` | Poll progress for batch jobs.     |

---

---

## 📄 Legal & Contribution

- **License**: Distributed under the [MIT License](LICENSE).
- **Contributing**: Please review [CONTRIBUTING](CONTRIBUTING.md) for development standards.
