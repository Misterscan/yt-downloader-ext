const BACKEND_URL = "http://127.0.0.1:5001";

// ── State ──
let currentFormat = "mp3";
let isPlaylist = false;
let playlistUrl = null;
let videoUrl = null;

// ── Quality options per format ──
const QUALITY_OPTIONS = {
  mp3: [
    { value: "320", label: "320 kbps — Best" },
    { value: "256", label: "256 kbps — High" },
    { value: "192", label: "192 kbps — Standard" },
    { value: "128", label: "128 kbps — Compact" },
  ],
  mp4: [
    { value: "2160", label: "4K (2160p)" },
    { value: "1440", label: "1440p" },
    { value: "1080", label: "1080p — Full HD" },
    { value: "720",  label: "720p — HD" },
    { value: "480",  label: "480p" },
    { value: "360",  label: "360p — Compact" },
  ],
};

function sanitizeFilename(name) {
  return (name || "youtube_download")
    .replace(/[\\/:*?"<>|]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 120) || "youtube_download";
}

// ── Populate quality dropdown ──
function populateQuality(format) {
  const sel = document.getElementById("qualitySelect");
  sel.innerHTML = "";
  for (const opt of QUALITY_OPTIONS[format]) {
    const o = document.createElement("option");
    o.value = opt.value;
    o.textContent = opt.label;
    sel.appendChild(o);
  }
  // Default: 192 for mp3, 1080 for mp4
  sel.value = format === "mp3" ? "192" : "1080";
}

// ── Format toggle ──
function initFormatToggle() {
  const toggle = document.getElementById("formatToggle");
  const buttons = toggle.querySelectorAll("button");
  const btnText = document.getElementById("btnText");
  const playlistBtnText = document.getElementById("playlistBtnText");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentFormat = btn.dataset.format;
      populateQuality(currentFormat);
      btnText.textContent = `Download ${currentFormat.toUpperCase()}`;
      if (playlistBtnText) {
        playlistBtnText.textContent = `Download Playlist as ZIP (${currentFormat.toUpperCase()})`;
      }
    });
  });
}

// ── Detect playlist from URL ──
function detectPlaylist(url) {
  // YouTube playlist URL patterns
  if (url.includes("list=")) {
    return true;
  }
  return false;
}

// ── Fetch video info ──
async function fetchVideoInfo(url) {
  const statusEl = document.getElementById("status");
  const loadingInfo = document.getElementById("loadingInfo");
  const metaContainer = document.getElementById("metaContainer");
  const dlBtn = document.getElementById("dlBtn");

  try {
    const response = await fetch(
      `${BACKEND_URL}/info?url=${encodeURIComponent(url)}`
    );
    
    let data;
    try {
      data = await response.json();
    } catch (parseErr) {
      throw new Error("Backend returned invalid data. Please completely restart the Flask server.");
    }

    if (data.error) {
      throw new Error(data.error);
    }

    // Populate UI
    document.getElementById("titleInput").value = data.title || "";
    document.getElementById("artistInput").value = data.artist || "";

    const thumbImg = document.getElementById("thumbnail");
    if (data.thumbnail) {
      thumbImg.src = data.thumbnail;
      thumbImg.style.display = "block";
      document.getElementById("thumbPlaceholder").style.display = "none";
    }

    // Playlist detection — use backend count if available, otherwise check URL
    if (data.playlist_count && data.playlist_count > 1) {
      isPlaylist = true;
      const badge = document.getElementById("playlistBadge");
      badge.classList.add("visible");
      document.getElementById("playlistCount").textContent = data.playlist_count;
      document.getElementById("playlistBadgeText").innerHTML =
        `Playlist detected — <b>${data.playlist_count}</b> videos`;
      document.getElementById("playlistBtn").hidden = false;
    } else if (detectPlaylist(videoUrl)) {
      // URL has list= but backend couldn't count (e.g. private playlist)
      isPlaylist = true;
      const badge = document.getElementById("playlistBadge");
      badge.classList.add("visible");
      document.getElementById("playlistBadgeText").textContent =
        "Playlist detected";
      document.getElementById("playlistBtn").hidden = false;
    }

    loadingInfo.hidden = true;
    metaContainer.hidden = false;
    dlBtn.disabled = false;
  } catch (err) {
    console.error(err);
    // If we're on a playlist page, still show the playlist button
    if (detectPlaylist(videoUrl)) {
      isPlaylist = true;
      const badge = document.getElementById("playlistBadge");
      badge.classList.add("visible");
      document.getElementById("playlistBadgeText").textContent =
        "Playlist detected (private?)";
      document.getElementById("playlistBtn").hidden = false;
      loadingInfo.hidden = true;
      statusEl.textContent = "Single download unavailable — use playlist ZIP";
    } else {
      statusEl.textContent = `Error: ${err.message}`;
      loadingInfo.textContent = "Could not load video info.";
    }
  }
}

// ── Init ──
document.addEventListener("DOMContentLoaded", async () => {
  initFormatToggle();
  populateQuality("mp3");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab.url;

  if (
    !url ||
    (!url.includes("youtube.com/watch") &&
      !url.includes("youtu.be/") &&
      !url.includes("youtube.com/playlist"))
  ) {
    document.getElementById("loadingInfo").textContent =
      "Please open a YouTube video or playlist!";
    return;
  }

  videoUrl = url;

  // If this is a playlist page, detect and show badge right away
  if (detectPlaylist(url)) {
    playlistUrl = url;
  }

  fetchVideoInfo(url);
});

// ── Single download ──
document.getElementById("dlBtn").addEventListener("click", async () => {
  const url = videoUrl;
  if (!url) return;

  const title = document.getElementById("titleInput").value;
  const artist = document.getElementById("artistInput").value;
  const quality = document.getElementById("qualitySelect").value;

  const btn = document.getElementById("dlBtn");
  const btnText = document.getElementById("btnText");
  const loader = document.getElementById("btnLoader");
  const statusEl = document.getElementById("status");

  const originalText = btnText.textContent;
  btnText.textContent = "Processing...";
  loader.style.display = "inline-block";
  btn.disabled = true;
  statusEl.textContent = "Downloading and processing (may take ~15s)...";

  const downloadParams = new URLSearchParams({
    url: url,
    format: currentFormat,
    quality: quality,
    title: title,
    artist: artist,
  });

  const downloadUrl = `${BACKEND_URL}/download?${downloadParams.toString()}`;
  const ext = currentFormat;
  const outputName = `${sanitizeFilename(title)}.${ext}`;

  try {
    chrome.downloads.download(
      {
        url: downloadUrl,
        filename: outputName,
        conflictAction: "uniquify",
        saveAs: true,
      },
      (downloadId) => {
        btnText.textContent = originalText;
        loader.style.display = "none";
        btn.disabled = false;

        if (chrome.runtime.lastError) {
          statusEl.textContent = `Error: ${chrome.runtime.lastError.message}`;
        } else {
          statusEl.textContent = "Download started!";
        }
      }
    );
  } catch (err) {
    console.error(err);
    alert("Make sure the helper is running on http://127.0.0.1:5001");
    btnText.textContent = originalText;
    loader.style.display = "none";
    btn.disabled = false;
  }
});

// ── Playlist ZIP download ──
document.getElementById("playlistBtn").addEventListener("click", async () => {
  const url = videoUrl;
  if (!url) return;

  const quality = document.getElementById("qualitySelect").value;

  const plBtn = document.getElementById("playlistBtn");
  const plBtnText = document.getElementById("playlistBtnText");
  const statusEl = document.getElementById("status");
  const progressContainer = document.getElementById("progressContainer");
  const progressFill = document.getElementById("progressFill");
  const progressText = document.getElementById("progressText");

  const originalText = plBtnText.textContent;
  plBtnText.textContent = "Preparing...";
  plBtn.disabled = true;
  statusEl.textContent = "Starting playlist download...";
  progressContainer.classList.add("visible");
  progressFill.style.width = "0%";
  progressText.textContent = "Preparing…";

  try {
    // 1. Start the playlist job
    const startRes = await fetch(`${BACKEND_URL}/playlist/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: url,
        format: currentFormat,
        quality: quality,
      }),
    });

    let startData;
    try {
      startData = await startRes.json();
    } catch (parseErr) {
      throw new Error("Backend route not found. Did you restart the Flask server?");
    }

    if (startData.error) throw new Error(startData.error);

    const jobId = startData.job_id;
    const total = startData.total;
    statusEl.textContent = `Downloading ${total} tracks...`;

    // 2. Poll for progress
    let done = false;
    while (!done) {
      await new Promise((r) => setTimeout(r, 2000));

      const pollRes = await fetch(`${BACKEND_URL}/playlist/status/${jobId}`);
      const pollData = await pollRes.json();

      if (pollData.error) throw new Error(pollData.error);

      const pct = Math.round((pollData.completed / pollData.total) * 100);
      progressFill.style.width = `${pct}%`;
      progressText.textContent = `${pollData.completed} / ${pollData.total} complete`;
      statusEl.textContent = pollData.current_title
        ? `Processing: ${pollData.current_title}`
        : `Downloading ${pollData.completed}/${pollData.total}...`;

      if (pollData.status === "done") {
        done = true;
      } else if (pollData.status === "error") {
        throw new Error(pollData.message || "Playlist download failed");
      }
    }

    // 3. Download the ZIP
    progressFill.style.width = "100%";
    progressText.textContent = "Preparing ZIP...";
    statusEl.textContent = "Packaging ZIP file...";

    chrome.downloads.download(
      {
        url: `${BACKEND_URL}/playlist/download/${jobId}`,
        filename: `playlist_${currentFormat}.zip`,
        conflictAction: "uniquify",
        saveAs: true,
      },
      (downloadId) => {
        if (chrome.runtime.lastError) {
          statusEl.textContent = `Error: ${chrome.runtime.lastError.message}`;
        } else {
          statusEl.textContent = "Playlist ZIP download started!";
          progressText.textContent = "Done!";
        }
        plBtnText.textContent = originalText;
        plBtn.disabled = false;
      }
    );
  } catch (err) {
    console.error(err);
    statusEl.textContent = `Error: ${err.message}`;
    plBtnText.textContent = originalText;
    plBtn.disabled = false;
    progressContainer.classList.remove("visible");
  }
});