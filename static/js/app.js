// ZenthYT — High-Speed Media Engine Frontend Controller
// Production Ready • Live Queue Engine • Precise Quality Selector

// ==========================================
// 0. API Base URL Resolution (Supports FastAPI & VS Code Live Server)
// ==========================================
function resolveApiBase() {
  if (typeof window === "undefined" || !window.location) return "";
  const proto = window.location.protocol;
  const port = window.location.port;
  if (proto === "file:" || (port && port !== "8000")) {
    return "http://localhost:8000";
  }
  return "";
}

const API_BASE = resolveApiBase();

// Global Application State
let currentVideoData = null;
let currentFormat = "mp3"; // 'mp3' or 'mp4'
let selectedAudioBitrate = "320k";
let selectedVideoResolution = "1080p";

// In-Memory Live Queue (No persistent past history - active session tasks only)
let liveQueue = [];

// DOM Elements
const form = document.getElementById("convert-form");
const urlInput = document.getElementById("video-url");
const fetchBtn = document.getElementById("fetch-btn");
const btnText = document.getElementById("btn-text");
const btnIcon = document.getElementById("btn-icon");
const btnSpinner = document.getElementById("btn-spinner");
const pasteBtn = document.getElementById("paste-btn");
const pasteHint = document.getElementById("paste-hint");
const pasteHintText = document.getElementById("paste-hint-text");
const errorBox = document.getElementById("error-box");
const errorMessage = document.getElementById("error-message");
const resultBox = document.getElementById("result-box");

// Media Preview Elements
const videoThumb = document.getElementById("video-thumb");
const videoDuration = document.getElementById("video-duration");
const videoTitle = document.getElementById("video-title");
const videoChannel = document.getElementById("video-channel");
const videoViews = document.getElementById("video-views");
const tabMp3 = document.getElementById("tab-mp3");
const tabMp4 = document.getElementById("tab-mp4");
const tabMp3Badge = document.getElementById("tab-mp3-badge");
const tabMp4Badge = document.getElementById("tab-mp4-badge");
const topMp3Wrapper = document.getElementById("top-mp3-select-wrapper");
const topMp4Wrapper = document.getElementById("top-mp4-select-wrapper");
const topBitrateSelect = document.getElementById("top-bitrate-select");
const topResolutionSelect = document.getElementById("top-resolution-select");
const audioQualityList = document.getElementById("audio-quality-list");
const videoQualityList = document.getElementById("video-quality-list");
const startDownloadBtn = document.getElementById("start-download-btn");
const downloadBtnText = document.getElementById("download-btn-text");

// Progress Bar Elements
const downloadProgressBar = document.getElementById("download-progress-bar");
const downloadStatusText = document.getElementById("download-status-text");
const downloadStateLabel = document.getElementById("download-state-label");
const downloadStatusBadge = document.getElementById("download-status-badge");
const downloadPercentBadge = document.getElementById("download-percent-badge");
const progressFill = document.getElementById("progress-fill");
const downloadBytesCounter = document.getElementById("download-bytes-counter");
const downloadSpeedText = document.getElementById("download-speed-text");
const downloadHintText = document.getElementById("download-hint-text");

// Queue Elements
const queueContainer = document.getElementById("queue-container");
const queueCount = document.getElementById("queue-count");

// ==========================================
// Safe JSON Fetcher (Prevents Unexpected token '<' errors)
// ==========================================
async function safeFetchJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (netErr) {
    throw new Error(
      "Cannot connect to ZenthYT backend. Please ensure the backend is running with 'python run.py' in your terminal on http://localhost:8000."
    );
  }

  const contentType = response.headers.get("content-type") || "";
  let data = null;

  if (contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch (parseErr) {
      throw new Error("Invalid response format received from backend.");
    }
  } else {
    const rawText = await response.text();
    console.warn("Non-JSON response received from server:", rawText.slice(0, 150));
    if (response.status === 404) {
      throw new Error(
        "API endpoint not found (404). If you opened this file with VS Code Live Server, please open http://localhost:8000 in your browser, or ensure 'python run.py' is running."
      );
    }
    throw new Error(
      `Backend returned status ${response.status}. Please make sure 'python run.py' is running on http://localhost:8000.`
    );
  }

  if (!response.ok) {
    throw new Error(data?.detail || `Error (${response.status}): Failed to process video.`);
  }

  return data;
}

// ==========================================
// 1. Clipboard & Paste Handling
// ==========================================

async function handlePasteClipboard() {
  hidePasteHint();
  hideError();

  try {
    if (!navigator.clipboard || !navigator.clipboard.readText) {
      throw new Error("Clipboard API not supported in this browser context.");
    }
    const text = await navigator.clipboard.readText();
    if (text && text.trim()) {
      urlInput.value = text.trim();
      hideError();
      hidePasteHint();
      if (isValidYoutubeInput(text.trim())) {
        await handleFetchVideo();
      }
    } else {
      showPasteHint("Clipboard is empty. Copy a YouTube link and try again.");
      urlInput.focus();
    }
  } catch (err) {
    console.warn("Clipboard access blocked or unsupported:", err);
    showPasteHint("Clipboard permission blocked by browser — press Ctrl+V to paste your link!");
    urlInput.focus();
    urlInput.select();
  }
}

function showPasteHint(msg) {
  if (pasteHint && pasteHintText) {
    pasteHintText.textContent = msg;
    pasteHint.classList.remove("hidden");
  }
}

function hidePasteHint() {
  if (pasteHint) {
    pasteHint.classList.add("hidden");
  }
}

// Listen for paste event directly on input (Ctrl+V / Right-Click -> Paste)
if (urlInput) {
  urlInput.addEventListener("paste", (e) => {
    hidePasteHint();
    hideError();
    
    let pastedData = "";
    if (e.clipboardData && e.clipboardData.getData) {
      pastedData = e.clipboardData.getData("text");
    }

    setTimeout(() => {
      const val = (pastedData || urlInput.value).trim();
      if (val) {
        urlInput.value = val;
        if (isValidYoutubeInput(val)) {
          handleFetchVideo();
        }
      }
    }, 60);
  });

  urlInput.addEventListener("input", () => {
    hidePasteHint();
    hideError();
  });
}

function isValidYoutubeInput(str) {
  if (!str) return false;
  return str.includes("youtube.com") || str.includes("youtu.be") || /^[a-zA-Z0-9_-]{11}$/.test(str);
}

// ==========================================
// 2. Fetch Video Metadata
// ==========================================

async function handleFetchVideo() {
  const url = urlInput.value.trim();
  if (!url) {
    showError("Please paste a valid YouTube video or Shorts link.");
    return null;
  }

  setLoading(true, "Fetching...");
  hideError();

  try {
    const data = await safeFetchJson(`${API_BASE}/api/info?url=${encodeURIComponent(url)}`);

    currentVideoData = data;
    renderVideoDetails(data);
    resultBox.classList.remove("hidden");
    resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return data;

  } catch (err) {
    showError(err.message || "Could not retrieve video details. Please verify the URL.");
    resultBox.classList.add("hidden");
    return null;
  } finally {
    setLoading(false);
  }
}

// ==========================================
// 3. Convert & Stream (Primary Action Button)
// ==========================================

async function handleConvertAndStream() {
  const url = urlInput.value.trim();
  if (!url) {
    showError("Please enter or paste a YouTube video or Shorts link.");
    urlInput.focus();
    return;
  }

  hideError();
  hidePasteHint();

  // If video metadata is already fetched and matches current input
  if (currentVideoData && (currentVideoData.url === url || currentVideoData.id === extractVideoId(url))) {
    triggerDownload();
    return;
  }

  // Otherwise, fetch info first and immediately trigger the download
  setLoading(true, "Converting & Streaming...");
  try {
    const data = await safeFetchJson(`${API_BASE}/api/info?url=${encodeURIComponent(url)}`);

    currentVideoData = data;
    renderVideoDetails(data);
    resultBox.classList.remove("hidden");
    resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Instantly stream the download
    triggerDownload();

  } catch (err) {
    showError(err.message || "Failed to process video. Please check the URL.");
  } finally {
    setLoading(false);
  }
}

// ==========================================
// 4. Render Video Details & Precise Quality Selectors
// ==========================================

function renderVideoDetails(data) {
  videoThumb.src = data.thumbnail;
  videoDuration.textContent = data.duration_formatted;
  videoTitle.textContent = data.title;
  videoChannel.textContent = data.channel;
  videoViews.textContent = data.views_formatted || "YouTube Video";

  renderAudioOptions(data.audio_formats);
  renderVideoOptions(data.video_formats);
  switchFormatTab(currentFormat);
}

function renderAudioOptions(formats) {
  if (!audioQualityList) return;
  audioQualityList.innerHTML = "";
  if (!formats || formats.length === 0) {
    audioQualityList.innerHTML = `<div class="text-xs text-slate-400 col-span-2 py-2 font-mono">Audio transcoding available (320k)</div>`;
    return;
  }

  // Ensure current selection is valid; otherwise default to recommended or first
  const hasSelected = formats.some(f => f.bitrate === selectedAudioBitrate);
  if (!selectedAudioBitrate || !hasSelected) {
    const defaultFmt = formats.find(f => f.recommended) || formats[0];
    selectedAudioBitrate = defaultFmt.bitrate;
  }

  // Sync top select & badge
  if (topBitrateSelect) {
    topBitrateSelect.value = selectedAudioBitrate;
  }
  if (tabMp3Badge) {
    tabMp3Badge.textContent = selectedAudioBitrate;
  }

  formats.forEach((fmt) => {
    const isSelected = fmt.bitrate === selectedAudioBitrate;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `quality-option p-2.5 rounded-xl border text-left flex items-center justify-between transition-all cursor-pointer active:scale-95 ${
      isSelected 
        ? "bg-[#FF4103]/15 border-[#FF4103] text-white shadow-[0_0_15px_rgba(255,65,3,0.3)] ring-1 ring-[#FF4103]/60" 
        : "bg-[#001018]/80 border-white/10 text-slate-300 hover:border-white/20 hover:bg-white/[0.03]"
    }`;
    btn.onclick = () => selectAudioBitrate(fmt.bitrate);

    btn.innerHTML = `
      <div class="flex items-center gap-2">
        <div class="w-3.5 h-3.5 rounded-full border ${isSelected ? 'border-[#FF4103] bg-[#FF4103] shadow-[0_0_8px_#FF4103]' : 'border-slate-600'} flex items-center justify-center">
          ${isSelected ? '<div class="w-1.5 h-1.5 rounded-full bg-white"></div>' : ''}
        </div>
        <span class="text-xs sm:text-sm font-medium font-mono ${isSelected ? 'text-white' : 'text-slate-300'}">${fmt.bitrate.toUpperCase()} MP3</span>
      </div>
      <div class="flex items-center gap-1.5">
        ${fmt.approx_size_mb ? `<span class="text-[11px] text-slate-400 font-mono">~${fmt.approx_size_mb} MB</span>` : ''}
        ${fmt.recommended ? `<span class="text-[10px] uppercase font-mono font-medium px-1.5 py-0.5 rounded bg-[#FF4103]/20 text-[#FF4103] border border-[#FF4103]/40">Studio HQ</span>` : ''}
      </div>
    `;
    audioQualityList.appendChild(btn);
  });
}

function renderVideoOptions(formats) {
  if (!videoQualityList) return;
  videoQualityList.innerHTML = "";
  if (!formats || formats.length === 0) {
    videoQualityList.innerHTML = `<div class="text-xs text-slate-400 col-span-2 py-2 font-mono">Default MP4 formats ready (1080p/720p/480p/360p)</div>`;
    return;
  }

  // Ensure current selection is valid; otherwise default to recommended (1080p) or first
  const hasSelected = formats.some(f => f.resolution === selectedVideoResolution);
  if (!selectedVideoResolution || !hasSelected) {
    const defaultFmt = formats.find(f => f.recommended) || formats[0];
    selectedVideoResolution = defaultFmt.resolution;
  }

  // Synchronize top dropdown options with all available video resolutions from YouTube
  if (topResolutionSelect) {
    let selectHtml = "";
    formats.forEach(f => {
      const isSelected = f.resolution === selectedVideoResolution;
      selectHtml += `<option value="${f.resolution}" ${isSelected ? "selected" : ""}>${f.resolution} ${f.approx_size_mb ? `(~${f.approx_size_mb} MB)` : ""}</option>`;
    });
    topResolutionSelect.innerHTML = selectHtml;
    topResolutionSelect.value = selectedVideoResolution;
  }

  if (tabMp4Badge) {
    tabMp4Badge.textContent = selectedVideoResolution;
  }

  formats.forEach((fmt) => {
    const isSelected = fmt.resolution === selectedVideoResolution;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `quality-option p-2.5 rounded-xl border text-left flex items-center justify-between transition-all cursor-pointer active:scale-95 ${
      isSelected 
        ? "bg-[#FF4103]/15 border-[#FF4103] text-white shadow-[0_0_15px_rgba(255,65,3,0.3)] ring-1 ring-[#FF4103]/60" 
        : "bg-[#001018]/80 border-white/10 text-slate-300 hover:border-white/20 hover:bg-white/[0.03]"
    }`;
    btn.onclick = () => selectVideoResolution(fmt.resolution);

    btn.innerHTML = `
      <div class="flex items-center gap-2">
        <div class="w-3.5 h-3.5 rounded-full border ${isSelected ? 'border-[#FF4103] bg-[#FF4103] shadow-[0_0_8px_#FF4103]' : 'border-slate-600'} flex items-center justify-center">
          ${isSelected ? '<div class="w-1.5 h-1.5 rounded-full bg-white"></div>' : ''}
        </div>
        <span class="text-xs sm:text-sm font-medium font-mono ${isSelected ? 'text-white' : 'text-slate-300'}">${fmt.resolution}</span>
      </div>
      <div class="flex items-center gap-1.5">
        ${fmt.approx_size_mb ? `<span class="text-[11px] text-slate-400 font-mono">~${fmt.approx_size_mb} MB</span>` : ''}
        ${fmt.height >= 1080 ? `<span class="text-[10px] uppercase font-mono font-medium px-1.5 py-0.5 rounded bg-[#FF4103]/15 text-[#FF4103] border border-[#FF4103]/30">${fmt.resolution === '4K' ? '4K' : (fmt.resolution === '2K' ? '2K' : 'HD')}</span>` : ''}
      </div>
    `;
    videoQualityList.appendChild(btn);
  });
}

function switchFormatTab(tab) {
  currentFormat = tab;

  if (tab === "mp3") {
    if (tabMp3) {
      tabMp3.className = "px-3.5 py-2 rounded-lg font-mono text-xs font-medium transition-all bg-[#00273a] text-white border border-[#FF4103]/60 shadow-sm flex items-center gap-1.5 cursor-pointer";
    }
    if (tabMp4) {
      tabMp4.className = "px-3.5 py-2 rounded-lg font-mono text-xs font-medium transition-all text-slate-400 hover:text-white flex items-center gap-1.5 cursor-pointer";
    }
    if (topMp3Wrapper) topMp3Wrapper.classList.remove("hidden");
    if (topMp4Wrapper) topMp4Wrapper.classList.add("hidden");
    if (audioQualityList) audioQualityList.classList.remove("hidden");
    if (videoQualityList) videoQualityList.classList.add("hidden");
  } else {
    if (tabMp4) {
      tabMp4.className = "px-3.5 py-2 rounded-lg font-mono text-xs font-medium transition-all bg-[#00273a] text-white border border-[#FF4103]/60 shadow-sm flex items-center gap-1.5 cursor-pointer";
    }
    if (tabMp3) {
      tabMp3.className = "px-3.5 py-2 rounded-lg font-mono text-xs font-medium transition-all text-slate-400 hover:text-white flex items-center gap-1.5 cursor-pointer";
    }
    if (topMp3Wrapper) topMp3Wrapper.classList.add("hidden");
    if (topMp4Wrapper) topMp4Wrapper.classList.remove("hidden");
    if (videoQualityList) videoQualityList.classList.remove("hidden");
    if (audioQualityList) audioQualityList.classList.add("hidden");
  }
  updateDownloadBtnText();
}

function selectAudioBitrate(bitrate) {
  selectedAudioBitrate = bitrate;
  if (topBitrateSelect) topBitrateSelect.value = bitrate;
  if (tabMp3Badge) tabMp3Badge.textContent = bitrate;
  if (currentVideoData) {
    renderAudioOptions(currentVideoData.audio_formats);
  }
  updateDownloadBtnText();
}

function selectVideoResolution(res) {
  selectedVideoResolution = res;
  if (topResolutionSelect) topResolutionSelect.value = res;
  if (tabMp4Badge) tabMp4Badge.textContent = res;
  if (currentVideoData) {
    renderVideoOptions(currentVideoData.video_formats);
  }
  updateDownloadBtnText();
}

function updateDownloadBtnText() {
  if (!downloadBtnText) return;
  if (currentFormat === "mp3") {
    downloadBtnText.textContent = `Download MP3 (${selectedAudioBitrate.toUpperCase()})`;
  } else {
    downloadBtnText.textContent = `Download MP4 (${selectedVideoResolution})`;
  }
}

// ==========================================
// 5. Trigger Streaming Download with Real-Time Progress Bar
// ==========================================

async function triggerDownload(overrideFormat = null, overrideQuality = null, overrideUrl = null, overrideMeta = null) {
  const targetUrl = overrideUrl || (currentVideoData ? currentVideoData.url : urlInput.value.trim());
  if (!targetUrl) {
    showError("Please enter or fetch a valid video link first.");
    return;
  }

  const fmt = overrideFormat || currentFormat;
  const q = overrideQuality || (fmt === "mp3" ? selectedAudioBitrate : selectedVideoResolution);
  const meta = overrideMeta || currentVideoData;

  const downloadUrl = `${API_BASE}/api/download?url=${encodeURIComponent(targetUrl)}&format=${fmt}&quality=${encodeURIComponent(q)}`;

  // 1. Reveal and Reset the Real Progress Bar Box
  if (downloadProgressBar) downloadProgressBar.classList.remove("hidden");
  
  if (progressFill) progressFill.style.width = "0%";
  if (downloadPercentBadge) downloadPercentBadge.textContent = "0%";
  if (downloadBytesCounter) downloadBytesCounter.textContent = "0.0 MB / ~ MB";
  if (downloadSpeedText) downloadSpeedText.textContent = "Initializing...";
  if (downloadStatusBadge) {
    downloadStatusBadge.textContent = "Transcoding";
    downloadStatusBadge.className = "text-[10px] uppercase px-2 py-0.5 rounded bg-[#FF4103]/20 text-[#FF4103] font-medium border border-[#FF4103]/30";
  }
  if (downloadStateLabel) {
    downloadStateLabel.textContent = `🚀 Transcoding ${fmt.toUpperCase()} (${q}) with FFmpeg 7.1...`;
  }
  if (downloadHintText) {
    downloadHintText.innerHTML = `
      <span class="material-symbols-outlined text-sm text-[#FF4103] animate-spin">progress_activity</span>
      <span>Server is extracting media chunks and converting to ${fmt.toUpperCase()}. Real-time stream will start shortly...</span>
    `;
  }

  // Update Download button state
  if (startDownloadBtn) {
    startDownloadBtn.disabled = true;
    startDownloadBtn.classList.add("opacity-75", "cursor-not-allowed");
  }
  if (downloadBtnText) {
    downloadBtnText.innerHTML = `<span class="animate-pulse">⏳ Streaming (${fmt.toUpperCase()} ${q})...</span>`;
  }

  // 2. Add to Session Live Queue with "transcoding" status
  const taskId = "task_" + Date.now();
  if (meta) {
    addToLiveQueue({
      id: taskId,
      title: meta.title || "YouTube Media",
      channel: meta.channel || "YouTube",
      thumbnail: meta.thumbnail || "",
      duration: meta.duration_formatted || "",
      format: fmt.toUpperCase(),
      quality: q,
      url: targetUrl,
      status: "transcoding",
      progress: 0,
      receivedMb: "0.0",
      totalMb: "~",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    });
  }

  // 3. Initiate Fetch Stream with Chunked Reader
  try {
    const response = await fetch(downloadUrl);

    if (!response.ok) {
      let errDetail = `Server error (${response.status})`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) errDetail = errJson.detail;
      } catch (e) {
        const textErr = await response.text();
        if (textErr) errDetail = textErr.slice(0, 150);
      }
      throw new Error(errDetail);
    }

    // Response arrived: Stream is connected!
    if (downloadStatusBadge) {
      downloadStatusBadge.textContent = "Streaming";
      downloadStatusBadge.className = "text-[10px] uppercase px-2 py-0.5 rounded bg-[#FF4103]/20 text-[#FF4103] font-medium border border-[#FF4103]/30";
    }
    if (downloadStateLabel) {
      downloadStateLabel.textContent = `⚡ Streaming ${fmt.toUpperCase()} (${q}) to browser...`;
    }

    // Determine Total Bytes from Content-Length
    const contentLengthHeader = response.headers.get("content-length");
    const totalBytes = contentLengthHeader ? parseInt(contentLengthHeader, 10) : 0;
    const totalMbStr = totalBytes > 0 ? (totalBytes / (1024 * 1024)).toFixed(1) + " MB" : "~ MB";

    // Extract accurate filename from Content-Disposition header
    let targetFilename = `${sanitizeForFilename(meta ? meta.title : "download")}.${fmt}`;
    const disposition = response.headers.get("content-disposition");
    if (disposition) {
      const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
      if (utf8Match && utf8Match[1]) {
        try { targetFilename = decodeURIComponent(utf8Match[1]); } catch (e) {}
      } else {
        const standardMatch = disposition.match(/filename="?([^";]+)"?/i);
        if (standardMatch && standardMatch[1]) {
          targetFilename = standardMatch[1];
        }
      }
    }

    // Read Incoming Stream Chunks
    const reader = response.body.getReader();
    const chunks = [];
    let receivedBytes = 0;
    let lastTime = performance.now();
    let bytesSinceLast = 0;
    let speedStr = "Streaming...";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      chunks.push(value);
      receivedBytes += value.length;
      bytesSinceLast += value.length;

      // Calculate speed every 200ms
      const now = performance.now();
      if (now - lastTime >= 200) {
        const elapsedSec = (now - lastTime) / 1000;
        const mbps = (bytesSinceLast / (1024 * 1024)) / elapsedSec;
        speedStr = `${mbps.toFixed(1)} MB/s`;
        bytesSinceLast = 0;
        lastTime = now;
      }

      const receivedMbStr = (receivedBytes / (1024 * 1024)).toFixed(1) + " MB";

      let percent = 0;
      if (totalBytes > 0) {
        percent = Math.min(100, Math.round((receivedBytes / totalBytes) * 100));
      } else {
        // Fallback smooth estimation up to 92% if Content-Length wasn't provided
        percent = Math.min(92, Math.round((receivedBytes / (1024 * 1024 * 20)) * 100));
      }

      // Live UI Updates
      if (progressFill) progressFill.style.width = `${percent}%`;
      if (downloadPercentBadge) downloadPercentBadge.textContent = `${percent}%`;
      if (downloadBytesCounter) downloadBytesCounter.textContent = `${receivedMbStr} / ${totalMbStr}`;
      if (downloadSpeedText) downloadSpeedText.textContent = speedStr;
      if (downloadStateLabel) downloadStateLabel.textContent = `Streaming (${percent}%)...`;

      // Update Live Queue Row
      updateTaskProgressInLiveQueue(taskId, percent, receivedMbStr, totalMbStr, "downloading");
    }

    // 4. Stream Completed: Assemble Blob and Trigger Browser File Save
    const contentType = response.headers.get("content-type") || (fmt === "mp3" ? "audio/mpeg" : "video/mp4");
    const fileBlob = new Blob(chunks, { type: contentType });
    const finalSizeMb = (receivedBytes / (1024 * 1024)).toFixed(1) + " MB";

    if (progressFill) progressFill.style.width = "100%";
    if (downloadPercentBadge) downloadPercentBadge.textContent = "100%";
    if (downloadBytesCounter) downloadBytesCounter.textContent = `${finalSizeMb} / ${finalSizeMb}`;
    if (downloadSpeedText) downloadSpeedText.textContent = "Finished";
    if (downloadStatusBadge) {
      downloadStatusBadge.textContent = "Delivered";
      downloadStatusBadge.className = "text-[10px] uppercase px-2 py-0.5 rounded bg-[#FF4103]/20 text-[#FF4103] font-medium border border-[#FF4103]/30";
    }
    if (downloadStateLabel) {
      downloadStateLabel.textContent = "✓ Download Complete!";
    }
    if (downloadHintText) {
      downloadHintText.innerHTML = `
        <span class="material-symbols-outlined text-sm text-[#FF4103]">check_circle</span>
        <span>File stream fully saved. Check your browser Downloads folder for <strong>${escapeHtml(targetFilename)}</strong>.</span>
      `;
    }

    // Save File via Object URL
    const blobUrl = URL.createObjectURL(fileBlob);
    const downloadAnchor = document.createElement("a");
    downloadAnchor.href = blobUrl;
    downloadAnchor.download = targetFilename;
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    document.body.removeChild(downloadAnchor);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);

    // Update Live Queue status
    completeTaskInLiveQueue(taskId, finalSizeMb);

    // Flash Download Button
    if (downloadBtnText) {
      downloadBtnText.textContent = `✓ Download Complete!`;
    }

  } catch (err) {
    console.error("Streaming download failed:", err);
    showError(err.message || "An error occurred during streaming conversion.");

    if (downloadStatusBadge) {
      downloadStatusBadge.textContent = "Error";
      downloadStatusBadge.className = "text-[10px] uppercase px-2 py-0.5 rounded bg-red-500/20 text-red-300 font-medium border border-red-500/30";
    }
    if (downloadStateLabel) {
      downloadStateLabel.textContent = "Download Failed";
    }
    if (downloadHintText) {
      downloadHintText.innerHTML = `
        <span class="material-symbols-outlined text-sm text-red-400">error</span>
        <span>${escapeHtml(err.message || "Stream interrupted.")}</span>
      `;
    }

    updateTaskStatusInLiveQueue(taskId, "failed");

  } finally {
    setTimeout(() => {
      if (startDownloadBtn) {
        startDownloadBtn.disabled = false;
        startDownloadBtn.classList.remove("opacity-75", "cursor-not-allowed");
      }
      updateDownloadBtnText();
    }, 2500);
  }
}

function sanitizeForFilename(str) {
  if (!str) return "media";
  return str.replace(/[\\/*?:"<>|]/g, "").replace(/\s+/g, " ").trim().slice(0, 100) || "media";
}

// ==========================================
// 6. Dynamic Live Queue (Session Only - No Past History)
// ==========================================

function addToLiveQueue(task) {
  liveQueue.unshift(task);
  if (liveQueue.length > 10) liveQueue.pop();
  renderQueue();
}

function updateTaskProgressInLiveQueue(taskId, percent, receivedMb, totalMb, status) {
  const task = liveQueue.find(t => t.id === taskId);
  if (task) {
    task.progress = percent;
    task.receivedMb = receivedMb;
    task.totalMb = totalMb;
    task.status = status;
    renderQueue();
  }
}

function completeTaskInLiveQueue(taskId, finalSize) {
  const task = liveQueue.find(t => t.id === taskId);
  if (task) {
    task.status = "completed";
    task.progress = 100;
    task.size = finalSize;
    renderQueue();
  }
}

function updateTaskStatusInLiveQueue(taskId, status) {
  const task = liveQueue.find(t => t.id === taskId);
  if (task) {
    task.status = status;
    renderQueue();
  }
}

function clearLiveQueue() {
  liveQueue = [];
  renderQueue();
}

function renderQueue() {
  if (!queueContainer) return;

  const activeCount = liveQueue.filter(t => t.status === "downloading" || t.status === "transcoding").length;
  if (queueCount) {
    queueCount.textContent = `${liveQueue.length} Task${liveQueue.length === 1 ? "" : "s"}${activeCount > 0 ? ` (${activeCount} active)` : ""}`;
  }

  if (liveQueue.length === 0) {
    queueContainer.innerHTML = `
      <div id="queue-empty-state" class="py-8 text-center text-slate-500 space-y-2">
        <span class="material-symbols-outlined text-4xl text-slate-600">hourglass_empty</span>
        <div class="text-sm font-mono text-slate-400">Live Queue is idle</div>
        <div class="text-xs text-slate-600">Paste any YouTube link above and click Convert &amp; Stream to start a download task!</div>
      </div>
    `;
    return;
  }

  let html = `
    <div class="flex justify-end pb-1">
      <button onclick="clearLiveQueue()" class="text-[11px] font-mono text-slate-400 hover:text-[#FF4103] transition-colors flex items-center gap-1 cursor-pointer">
        <span class="material-symbols-outlined text-xs">clear_all</span>
        <span>Clear Queue</span>
      </button>
    </div>
    <div class="space-y-3">
  `;

  liveQueue.forEach((item) => {
    const isMp3 = item.format === "MP3";
    const badgeBg = "bg-[#FF4103]/15 text-[#FF4103] border border-[#FF4103]/30";
    const isDownloading = item.status === "downloading" || item.status === "transcoding";
    const isCompleted = item.status === "completed";
    const isFailed = item.status === "failed";

    html += `
      <div class="glass-card rounded-2xl p-3.5 sm:p-4 border ${isDownloading ? 'border-[#FF4103]/50 bg-[#FF4103]/[0.05]' : 'border-white/10'} flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all">
        <div class="flex items-center gap-3 min-w-0">
          <div class="relative w-14 h-10 sm:w-16 sm:h-11 rounded-lg overflow-hidden bg-black shrink-0 border border-white/10">
            ${item.thumbnail ? `<img src="${item.thumbnail}" alt="" class="w-full h-full object-cover">` : `<div class="w-full h-full flex items-center justify-center text-slate-600"><span class="material-symbols-outlined text-sm">movie</span></div>`}
            ${item.duration ? `<span class="absolute bottom-0.5 right-0.5 px-1 py-0.2 rounded bg-black/80 font-mono text-[9px] text-white">${item.duration}</span>` : ""}
            ${isDownloading ? `
              <!-- Mini Audio Equalizer Visualizer in #FF4103 -->
              <div class="absolute bottom-0.5 left-0.5 flex items-end gap-0.5 h-3 px-1 py-0.5 bg-black/70 rounded backdrop-blur-sm">
                <span class="w-0.5 bg-[#FF4103] rounded-full bar-1"></span>
                <span class="w-0.5 bg-[#FF4103] rounded-full bar-2"></span>
                <span class="w-0.5 bg-[#FF4103] rounded-full bar-3"></span>
                <span class="w-0.5 bg-[#FF4103] rounded-full bar-4"></span>
              </div>
            ` : ""}
          </div>
          <div class="min-w-0">
            <h4 class="text-xs sm:text-sm font-medium text-white truncate leading-snug hover:text-[#FF4103] transition-colors">${escapeHtml(item.title)}</h4>
            <div class="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400 font-mono">
              <span class="truncate max-w-[120px] sm:max-w-[180px] text-slate-400">${escapeHtml(item.channel)}</span>
              <span>•</span>
              <span class="px-1.5 py-0.2 rounded text-[10px] uppercase font-medium border ${badgeBg}">${item.format} ${item.quality}</span>
              <span class="hidden sm:inline text-slate-500">${item.timestamp}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3 shrink-0 self-end sm:self-center">
          ${isDownloading ? `
            <div class="space-y-1.5 w-36 sm:w-48">
              <div class="flex items-center justify-between text-[10px] font-mono">
                <span class="text-[#FF4103] font-medium flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-[#FF4103] animate-ping"></span>
                  <span>${item.status === 'transcoding' ? 'Transcoding' : item.progress + '%'}</span>
                </span>
                <span class="text-slate-300 font-mono font-medium">${item.receivedMb || '0'} MB</span>
              </div>
              <!-- Real Candy-Stripe Live Progress Track -->
              <div class="w-full h-2 rounded-full bg-[#001018] border border-white/10 overflow-hidden relative">
                <div class="h-full progress-watermelon rounded-full transition-all duration-150 shadow-[0_0_10px_#FF4103]" style="width: ${item.progress || 0}%"></div>
              </div>
            </div>
          ` : (isCompleted ? `
            <span class="flex items-center gap-1.5 text-[11px] text-[#FF4103] font-mono bg-[#FF4103]/10 px-2.5 py-1 rounded-full border border-[#FF4103]/30 font-medium shadow-sm">
              <span class="w-1.5 h-1.5 rounded-full bg-[#FF4103]"></span>
              <span>Delivered (${item.size || (item.receivedMb ? item.receivedMb : 'HQ')})</span>
            </span>
            <button 
              type="button" 
              onclick="triggerDownload('${item.format.toLowerCase()}', '${item.quality}', '${escapeHtml(item.url)}')" 
              class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-[#FF4103]/15 text-slate-200 hover:text-white text-xs font-mono font-medium transition-all flex items-center gap-1.5 border border-white/10 hover:border-[#FF4103]/40 cursor-pointer active:scale-95 shadow-sm"
              title="Download again"
            >
              <span class="material-symbols-outlined text-sm text-[#FF4103]">download</span>
              <span class="hidden sm:inline">Download</span>
            </button>
          ` : `
            <span class="flex items-center gap-1 text-[11px] text-rose-400 font-mono bg-rose-500/10 px-2 py-1 rounded-full border border-rose-500/20 font-medium">
              <span class="material-symbols-outlined text-xs text-rose-400">error</span>
              <span>Failed</span>
            </span>
            <button 
              type="button" 
              onclick="triggerDownload('${item.format.toLowerCase()}', '${item.quality}', '${escapeHtml(item.url)}')" 
              class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white text-xs font-mono font-medium transition-all flex items-center gap-1.5 border border-white/10 hover:border-rose-500/40 cursor-pointer active:scale-95"
              title="Retry download"
            >
              <span class="material-symbols-outlined text-sm text-rose-400">refresh</span>
              <span class="hidden sm:inline">Retry</span>
            </button>
          `)}
        </div>
      </div>
    `;
  });

  html += `</div>`;
  queueContainer.innerHTML = html;
}

// ==========================================
// 7. Utility Functions
// ==========================================

function extractVideoId(url) {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|shorts\/|watch\?v=|&v=)([^#&?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11) ? match[2] : null;
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function setLoading(isLoading, text = "Loading...") {
  if (isLoading) {
    btnText.textContent = text;
    btnIcon.classList.add("hidden");
    btnSpinner.classList.remove("hidden");
    fetchBtn.disabled = true;
  } else {
    btnText.textContent = "Convert & Stream";
    btnIcon.classList.remove("hidden");
    btnSpinner.classList.add("hidden");
    fetchBtn.disabled = false;
  }
}

function showError(msg) {
  if (errorMessage && errorBox) {
    errorMessage.textContent = msg;
    errorBox.classList.remove("hidden");
  }
}

function hideError() {
  if (errorBox) {
    errorBox.classList.add("hidden");
  }
}

// ==========================================
// 8. Health Check & Initialization
// ==========================================

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      const statusEl = document.getElementById("system-status");
      if (statusEl) {
        statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-[#FF4103] animate-pulse"></span><span>All Nodes Operational • Engine Active • Direct Stream</span>`;
      }
    }
  } catch (e) {
    console.warn("Backend health check:", e);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Purge any legacy localStorage history so UI stays pure Live Queue
  try {
    localStorage.removeItem("zenthy_recent_conversions");
  } catch (e) {}

  renderQueue();
  checkHealth();
});
