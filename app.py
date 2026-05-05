import os
import re
import shutil
import uuid
import zipfile
import threading
import yt_dlp
import glob
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found. Ensure the backend is updated and running."}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": f"Internal server error: {str(e)}"}), 500

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# ── In-memory job tracker for playlist downloads ──
playlist_jobs = {}


def sanitize_title(title):
    # Keep filenames simple and safe across platforms.
    cleaned = re.sub(r"[^A-Za-z0-9 _.-]", "", title or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "youtube_download"


def next_available_base(base_name, directory=None):
    target_dir = directory or DOWNLOAD_DIR
    candidate = base_name
    counter = 1
    while glob.glob(os.path.join(target_dir, f"{candidate}.*")):
        counter += 1
        candidate = f"{base_name} ({counter})"
    return candidate


def resolve_ffmpeg_location():
    # launchd often has a minimal PATH; provide Homebrew fallback.
    env_loc = os.getenv('FFMPEG_LOCATION')
    if env_loc:
        return env_loc

    ffmpeg_bin = shutil.which('ffmpeg')
    if ffmpeg_bin:
        return os.path.dirname(ffmpeg_bin)

    # Default Homebrew prefix on Apple Silicon.
    fallback = '/opt/homebrew/bin'
    if os.path.exists(os.path.join(fallback, 'ffmpeg')):
        return fallback

    return None


def build_ydl_opts(format_type, quality, output_tmpl, ffmpeg_location, noplaylist=True):
    """Build yt-dlp option dict based on format and quality."""
    if format_type == 'mp3':
        fmt = 'bestaudio/best'
    else:
        # MP4: pick best mp4 video up to the requested height + m4a audio
        fmt = f'bestvideo[ext=mp4][height<={quality}]+bestaudio[ext=m4a]/best[ext=mp4][height<={quality}]/best[ext=mp4]/best'

    ydl_opts = {
        'format': fmt,
        'outtmpl': output_tmpl,
        'noplaylist': noplaylist,
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': format_type == 'mp3',  # Thumbnails only for MP3 embedding
    }

    if format_type == 'mp4':
        ydl_opts['merge_output_format'] = 'mp4'

    if ffmpeg_location:
        ydl_opts['ffmpeg_location'] = ffmpeg_location

    # Postprocessors
    postprocessors = []

    if format_type == 'mp3':
        postprocessors.append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': str(quality),
        })
        postprocessors.append({
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        })
    elif format_type == 'mp4':
        postprocessors.append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        })

    ydl_opts['postprocessors'] = postprocessors
    return ydl_opts


def embed_mp3_artwork(filename, file_base, info, ffmpeg_location, directory=None):
    """Crop thumbnail to square and embed into MP3 as cover art."""
    target_dir = directory or DOWNLOAD_DIR

    thumb_files = []
    for ext in ['webp', 'jpg', 'jpeg', 'png']:
        thumb_files.extend(glob.glob(os.path.join(target_dir, f"{file_base}.{ext}")))

    if not thumb_files:
        return

    thumb_path = thumb_files[0]
    cropped_thumb_path = os.path.join(target_dir, f"{file_base}_square.jpg")

    # 1. Crop to square
    crop_cmd = [
        'ffmpeg', '-y', '-i', thumb_path,
        '-vf', "crop='min(iw,ih)':'min(iw,ih)'",
        cropped_thumb_path
    ]
    if ffmpeg_location:
        crop_cmd[0] = os.path.join(ffmpeg_location, 'ffmpeg')

    crop_res = subprocess.run(crop_cmd, capture_output=True, text=True)
    if crop_res.returncode != 0:
        print(f"Crop failed: {crop_res.stderr}")

    if os.path.exists(cropped_thumb_path):
        # 2. Embed into MP3
        temp_mp3 = os.path.join(target_dir, f"{file_base}_tagged.mp3")
        embed_cmd = [
            'ffmpeg', '-y', '-i', filename, '-i', cropped_thumb_path,
            '-map', '0:0', '-map', '1:0', '-c', 'copy',
            '-map_metadata', '0',
            '-id3v2_version', '3',
            '-metadata', f'title={info.get("title", "")}',
            '-metadata', f'artist={info.get("artist", "")}',
            '-metadata:s:v', 'title=Album cover',
            '-metadata:s:v', 'comment=Cover (Front)',
            temp_mp3
        ]
        if ffmpeg_location:
            embed_cmd[0] = os.path.join(ffmpeg_location, 'ffmpeg')

        embed_res = subprocess.run(embed_cmd, capture_output=True, text=True)
        if embed_res.returncode != 0:
            print(f"Embed failed: {embed_res.stderr}")

        if os.path.exists(temp_mp3):
            os.replace(temp_mp3, filename)

        try:
            os.remove(cropped_thumb_path)
        except Exception:
            pass

    # Cleanup original thumbnails
    for thumb in thumb_files:
        try:
            os.remove(thumb)
        except Exception:
            pass


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return "YouTube Downloader Backend is running!"


@app.route('/info', methods=['GET'])
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    title = None
    artist = None
    thumbnail = None
    duration = None
    playlist_count = 0
    is_playlist_page = '/playlist' in url and 'watch' not in url

    # ── Step 1: Get single-video info (always reliable) ──
    if not is_playlist_page:
        video_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        try:
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            title = info.get('title')
            artist = info.get('artist') or info.get('uploader')
            thumbnail = info.get('thumbnail')
            duration = info.get('duration')
        except Exception as e:
            print(f"Error fetching video info: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # ── Step 2: Attempt playlist count (separate try — may fail on private) ──
    if 'list=' in url:
        playlist_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'noplaylist': False,
        }
        try:
            with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                pl_info = ydl.extract_info(url, download=False)

            if pl_info.get('_type') == 'playlist':
                entries = list(pl_info.get('entries') or [])
                playlist_count = pl_info.get('playlist_count') or len(entries)

                # If we're on a pure playlist page, grab info from the first entry
                if is_playlist_page and entries:
                    first = next((e for e in entries if e), None)
                    if first:
                        title = first.get('title', title)
                        thumbnail = (first.get('thumbnail')
                                     or (first.get('thumbnails') or [{}])[-1].get('url')
                                     or thumbnail)
                        artist = first.get('artist') or first.get('uploader') or artist
        except Exception as e:
            # Playlist extraction failed (private, deleted, etc.) — that's fine,
            # we still have the single-video info and the frontend can detect list= in the URL
            print(f"Playlist extraction failed (non-fatal): {str(e)}")

    if artist and artist.endswith(' - Topic'):
        artist = artist.replace(' - Topic', '')

    # If we have nothing at all (pure playlist page that failed), return error
    if not title and not thumbnail:
        return jsonify({"error": "Could not load info. The playlist may be private."}), 400

    return jsonify({
        "title": title,
        "artist": artist,
        "thumbnail": thumbnail,
        "duration": duration,
        "original_url": url,
        "playlist_count": playlist_count,
    })


@app.route('/download', methods=['GET', 'POST'])
def download():
    # Allow GET or POST for flexibility
    if request.method == 'POST':
        data = request.json
        url = data.get('url')
        format_type = data.get('format', 'mp3')
        quality = data.get('quality', '192' if format_type == 'mp3' else '1080')
        custom_title = data.get('title')
        custom_artist = data.get('artist')
    else:
        url = request.args.get('url')
        format_type = request.args.get('format', 'mp3')
        quality = request.args.get('quality', '192' if format_type == 'mp3' else '1080')
        custom_title = request.args.get('title')
        custom_artist = request.args.get('artist')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Extract info for default title if not provided
    info_opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": f"Metadata extraction failed: {str(e)}"}), 500

    raw_title = custom_title or info.get('title', 'youtube_download')
    safe_title = sanitize_title(raw_title)
    file_base = next_available_base(safe_title)
    output_tmpl = os.path.join(DOWNLOAD_DIR, f"{file_base}.%(ext)s")

    ffmpeg_location = resolve_ffmpeg_location()

    ydl_opts = build_ydl_opts(format_type, quality, output_tmpl, ffmpeg_location, noplaylist=True)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info['title'] = custom_title or info.get('title')
            info['artist'] = custom_artist or info.get('artist') or info.get('uploader')
            if info['artist'] and info['artist'].endswith(' - Topic'):
                info['artist'] = info['artist'].replace(' - Topic', '')

            ydl.process_info(info)

        # Check for the resulting file
        expected_ext = 'mp3' if format_type == 'mp3' else 'mp4'
        files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_base}.{expected_ext}"))

        # Fallback — if format is mp4, yt-dlp may produce mkv/webm
        if not files and format_type == 'mp4':
            for ext in ['mkv', 'webm', 'mp4']:
                files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_base}.{ext}"))
                if files:
                    break

        if files:
            filename = files[0]

            # Handle thumbnail embedding for MP3
            if format_type == "mp3":
                embed_mp3_artwork(filename, file_base, info, ffmpeg_location)

            output_name = os.path.basename(filename)
            mimetype = 'audio/mpeg' if format_type == 'mp3' else 'video/mp4'

            # Stream the file and delete it after the request finishes
            def generate():
                with open(filename, 'rb') as f:
                    yield from f
                try:
                    os.remove(filename)
                    # Cleanup residual files if any (like leftover thumbnails)
                    # yt-dlp usually cleans them but just in case
                    for residual in glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_base}.*")):
                         os.remove(residual)
                except Exception:
                    pass

            return app.response_class(
                generate(),
                mimetype=mimetype,
                headers={"Content-Disposition": f"attachment; filename=\"{output_name}\""}
            )
        else:
            # Cleanup any residual files even on failure
            for residual in glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_base}.*")):
                try: os.remove(residual)
                except Exception: pass
            return jsonify({"error": "Download failed: File not produced"}), 500

    except Exception as e:
        print(f"Error during download: {str(e)}")
        # Cleanup
        for residual in glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_base}.*")):
            try: os.remove(residual)
            except Exception: pass
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# Playlist ZIP endpoints
# ──────────────────────────────────────────────

@app.route('/playlist/start', methods=['POST'])
def playlist_start():
    """Start an async playlist download job. Returns a job_id for polling."""
    data = request.json or {}
    url = data.get('url')
    format_type = data.get('format', 'mp3')
    quality = data.get('quality', '192' if format_type == 'mp3' else '1080')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Extract playlist entries
    info_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'noplaylist': False,
    }

    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": f"Failed to extract playlist: {str(e)}"}), 500

    entries = []
    if info.get('_type') == 'playlist':
        for entry in (info.get('entries') or []):
            if entry:
                entry_url = entry.get('url') or entry.get('webpage_url')
                if entry_url:
                    # Make sure we have a full URL
                    if not entry_url.startswith('http'):
                        entry_url = f"https://www.youtube.com/watch?v={entry.get('id', entry_url)}"
                    entries.append({
                        'url': entry_url,
                        'title': entry.get('title', 'Unknown'),
                    })
    else:
        return jsonify({"error": "URL is not a playlist"}), 400

    if not entries:
        return jsonify({"error": "No entries found in playlist"}), 400

    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(DOWNLOAD_DIR, f"playlist_{job_id}")
    os.makedirs(job_dir, exist_ok=True)

    job = {
        'status': 'running',
        'total': len(entries),
        'completed': 0,
        'current_title': '',
        'message': '',
        'format': format_type,
        'quality': quality,
        'job_dir': job_dir,
        'zip_path': None,
        'playlist_title': sanitize_title(info.get('title', 'playlist')),
    }
    playlist_jobs[job_id] = job

    # Run the download in a background thread
    thread = threading.Thread(
        target=_run_playlist_download,
        args=(job_id, entries, format_type, quality, job_dir),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "job_id": job_id,
        "total": len(entries),
    })


def _run_playlist_download(job_id, entries, format_type, quality, job_dir):
    """Background thread: download each entry, then create ZIP."""
    job = playlist_jobs[job_id]
    ffmpeg_location = resolve_ffmpeg_location()

    for i, entry in enumerate(entries):
        try:
            job['current_title'] = entry['title']

            safe_title = sanitize_title(entry['title'])
            file_base = next_available_base(safe_title, directory=job_dir)
            output_tmpl = os.path.join(job_dir, f"{file_base}.%(ext)s")

            ydl_opts = build_ydl_opts(format_type, quality, output_tmpl, ffmpeg_location, noplaylist=True)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([entry['url']])

            # MP3 artwork embedding
            if format_type == 'mp3':
                ext = 'mp3'
                files = glob.glob(os.path.join(job_dir, f"{file_base}.{ext}"))
                if files:
                    # Build a minimal info dict for embed
                    embed_info = {'title': entry['title'], 'artist': ''}
                    embed_mp3_artwork(files[0], file_base, embed_info, ffmpeg_location, directory=job_dir)

        except Exception as e:
            print(f"Playlist item {i+1} failed: {str(e)}")
            # Continue with next track instead of aborting

        job['completed'] = i + 1

    # Create ZIP
    try:
        playlist_name = job.get('playlist_title', 'playlist')
        zip_path = os.path.join(DOWNLOAD_DIR, f"{playlist_name}_{job_id}.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(job_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = file  # Flat archive
                    zf.write(file_path, arcname)

        job['zip_path'] = zip_path
        job['status'] = 'done'
        job['current_title'] = ''

        # Cleanup individual files
        shutil.rmtree(job_dir, ignore_errors=True)

    except Exception as e:
        job['status'] = 'error'
        job['message'] = str(e)
        print(f"ZIP creation failed: {str(e)}")


@app.route('/playlist/status/<job_id>', methods=['GET'])
def playlist_status(job_id):
    """Poll the progress of a playlist download job."""
    job = playlist_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "status": job['status'],
        "total": job['total'],
        "completed": job['completed'],
        "current_title": job['current_title'],
        "message": job.get('message', ''),
    })


@app.route('/playlist/download/<job_id>', methods=['GET'])
def playlist_download(job_id):
    """Download the finished ZIP for a playlist job."""
    job = playlist_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job['status'] != 'done' or not job.get('zip_path'):
        return jsonify({"error": "ZIP not ready yet"}), 400

    zip_path = job['zip_path']

    def generate():
        with open(zip_path, 'rb') as f:
            yield from f
        # Cleanup after download
        try:
            os.remove(zip_path)
        except Exception:
            pass
        # Remove job from memory
        playlist_jobs.pop(job_id, None)

    zip_name = os.path.basename(zip_path)
    return app.response_class(
        generate(),
        mimetype='application/zip',
        headers={"Content-Disposition": f"attachment; filename=\"{zip_name}\""}
    )


if __name__ == '__main__':
    # launchd-friendly defaults; can be overridden via env vars.
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5001'))
    app.run(host=host, port=port, debug=False)
