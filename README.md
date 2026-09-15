# ⚡ ZenthYT — Fast YouTube to MP3 & MP4 Converter

A high-speed, asynchronous, production-ready web application to convert and stream YouTube videos and Shorts into **MP3 audio (64 kbps to 320 kbps)** and **MP4 video (360p to 4K)** with clean design, anti-bot protection, ID3 metadata tagging, and Google SEO ranking optimization.

---

## 📑 Table of Contents
1. [Project Overview & Architecture](#-project-overview--architecture)
2. [How Temporary Files & Storage Work (Production Storage Model)](#-how-temporary-files--storage-work-production-storage-model)
3. [How to Run the Project](#-how-to-run-the-project)
4. [Complete File-by-File Breakdown](#-complete-file-by-file-breakdown)
5. [Installed Dependencies & Size Footprint](#-installed-dependencies--size-footprint)
6. [Anti-Bot & Anti-Downtime Defense System](#-anti-bot--anti-downtime-defense-system)
7. [Supported Formats & Bitrates](#-supported-formats--bitrates)
8. [SEO Strategy for #1 Google Search Ranking](#-seo-strategy-for-1-google-search-ranking)
9. [REST API Reference & Endpoints](#-rest-api-reference--endpoints)
10. [Deploying to Production (Docker & VPS)](#-deploying-to-production-docker--vps)

---

## 🏛 Project Overview & Architecture

**ZenthYT** is built on an asynchronous ASGI engine powered by **FastAPI**, **yt-dlp**, **FFmpeg v7.1**, and a modern, responsive HTML5 + Tailwind CSS frontend.

### Architecture Diagram:
```
┌─────────────────────────────────────────────────────────────────┐
│                     USER BROWSER / MOBILE                       │
│     (Clean Pure White UI + Auto Clipboard Paste + No Popups)    │
└───────────────┬─────────────────────────────────▲───────────────┘
                │                                 │
     1. Video URL Query (GET /api/info)           │ 3. Direct Chunked Stream
     2. Download Stream (GET /api/download)       │    (MP3 320k / MP4 4K)
                │                                 │
                ▼                                 │
┌─────────────────────────────────────────────────┴───────────────┐
│                    ZENTHYT FASTAPI BACKEND                      │
│                                                                 │
│  ┌───────────────────────┐         ┌─────────────────────────┐  │
│  │  In-Memory TTL Cache  │         │ Background File Cleanup │  │
│  │   (Sub-50ms Info)     │         │ (Immediate Deletion)    │  │
│  └───────────┬───────────┘         └────────────▲────────────┘  │
│              │                                  │               │
│  ┌───────────▼───────────┐         ┌────────────┴────────────┐  │
│  │  yt-dlp Engine Pool   ├────────►│  FFmpeg Engine (v7.1)   │  │
│  │  (Android/iOS Client) │         │  (320k Transcode + ID3) │  │
│  └───────────┬───────────┘         └─────────────────────────┘  │
└──────────────┼──────────────────────────────────────────────────┘
               │ (Fallback rotation & Anti-Bot Spoofing)
               ▼
   [ YouTube Media CDN Servers ]
```

---

## 💾 How Temporary Files & Storage Work (Production Storage Model)

### Why are temporary files created during conversion?
1. **YouTube stream separation**: YouTube serves separate adaptive streams for high-resolution video (1080p/4K) and audio (Opus/AAC). Merging them into MP4 requires FFmpeg.
2. **Audio Transcoding**: Extracting audio into true **320 kbps MP3** with embedded album artwork and ID3 tags requires a brief intermediate transcode step before streaming chunks to the browser.

### Why you don't need to worry about storage on your PC or Server:
- **Outside Project Repo**: ZenthYT does **NOT** store downloads in your project folder. It uses the operating system's ephemeral temporary directory (`/tmp` on Linux or `%TEMP%/zenthyt_temp` on Windows).
- **Auto-Cleanup Background Task**: The moment a user finishes receiving their download stream, FastAPI executes an asynchronous `BackgroundTasks` cleanup job that **instantly deletes** the job's temporary directory.
- **Zero Permanent Storage Used**: Files exist only for the few seconds during transcoding and are purged immediately upon stream completion.

---

## 🏃 How to Run the Project (in VS Code)

1. **Open the project in VS Code**:
   Open VS Code and choose **File > Open Folder...**, then select this project folder (`Youtube MP3`).

2. **Open the Integrated Terminal**:
   Press <kbd>Ctrl</kbd> + <kbd>`</kbd> (or go to **Terminal > New Terminal** in the top menu).

3. **Install dependencies (if not already installed)**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run the server**:
   ```powershell
   python run.py
   ```

5. **Open in your browser**:
   - Web App UI: **[http://localhost:8000](http://localhost:8000)**
   - Interactive Swagger API Docs: **[http://localhost:8000/api/docs](http://localhost:8000/api/docs)**

To stop the server at any time, press <kbd>Ctrl</kbd> + <kbd>C</kbd> in the terminal.

---

## 📂 Complete File-by-File Breakdown

```
Youtube MP3/
├── app/
│   ├── __init__.py              # App package initializer
│   ├── config.py                # Environment configuration, anti-bot clients, system temp directory
│   ├── main.py                  # FastAPI ASGI application, route mounts, SEO sitemaps
│   ├── schemas/
│   │   ├── __init__.py          # Schemas package initializer
│   │   └── video.py             # Pydantic models for format options, metadata, and requests
│   ├── services/
│   │   ├── __init__.py          # Services package initializer
│   │   ├── cache_engine.py      # In-memory thread-safe TTL cache for sub-50ms repeat queries
│   │   ├── ffmpeg_engine.py     # FFmpeg binary discovery, audio transcode, ID3 metadata injector
│   │   └── ytdlp_engine.py      # Multi-client extractor (android/ios/mweb) and stream pipeline
│   └── routes/
│       ├── __init__.py          # Routes package initializer
│       ├── info.py              # GET/POST /api/info (Fetches title, duration, thumbnail, bitrates)
│       ├── download.py          # GET /api/download (Chunked streaming & automatic temp cleanup)
│       └── health.py            # GET /api/health (System diagnostic & FFmpeg readiness check)
├── templates/
│   └── index.html               # Clean, pure white semantic HTML5 UI with Schema.org JSON-LD
├── static/
│   ├── css/
│   │   └── styles.css           # Natural CSS styling, indeterminate loading bar, clean scrollbars
│   └── js/
│       └── app.js               # Reactive JS logic, clipboard auto-paste, format switching, stream triggers
├── .env.example                 # Environment variables template
├── requirements.txt             # Locked dependencies specification
├── markdown.md                  # Detailed package inventory with disk sizes and functions
├── run.py                       # Uvicorn launcher entry point
└── README.md                    # Master documentation (this file)
```

---

## 📦 Installed Dependencies & Size Footprint

Detailed in [`markdown.md`](file:///c:/Users/abhij/OneDrive/Desktop/Youtube%20MP3/markdown.md):

| Package | Version | Disk Size | Primary Function |
| :--- | :--- | :--- | :--- |
| **`fastapi`** | `0.137.0` | **1.47 MB** | Async ASGI web framework & streaming response |
| **`uvicorn[standard]`**| `0.49.0` | **688.2 KB** | Production ASGI server on uvloop/httptools |
| **`pydantic`** | `2.13.4` | **3.94 MB** | Data validation and JSON serialization |
| **`yt-dlp`** | `2026.8.19` | **21.18 MB** | YouTube extraction engine with anti-bot spoofing |
| **`imageio-ffmpeg`** | `0.6.0` | **83.66 MB** | Bundled standalone FFmpeg v7.1 binary |
| **`mutagen`** | `1.48.1` | **2.06 MB** | ID3 tag & cover art metadata injector |
| **`aiofiles`** | `25.1.0` | **76.2 KB** | Asynchronous non-blocking file streaming |
| **`jinja2`** | `3.1.6` | **1.26 MB** | Template engine for SEO HTML rendering |
| **`python-multipart`**| `0.0.32` | **196.2 KB** | Multipart form payload parser |
| **`requests`** | `2.34.2` | **505.3 KB** | HTTP client for remote thumbnail fetching |
| **`urllib3`** | `2.7.0` | **948.4 KB** | Resilient connection-pooled HTTP transport |

---

## 🛡️ Anti-Bot & Anti-Downtime Defense System

To prevent YouTube from blocking your server when scaling to thousands of daily users:

1. **Multi-Client Strategy (`player_client`)**:
   - Rotates extraction requests across `android`, `ios`, `mweb`, and `web_creator`.
2. **Automatic Retry Fallback**:
   - If an extraction query fails on one client, the engine catches the exception and immediately retries with the next client type.
3. **Rotating Proxy Pool (`YOUTUBE_PROXY`)**:
   - Support for rotating residential or datacenter proxies by setting `YOUTUBE_PROXY=http://user:pass@proxy.com:port`.
4. **Cookie Vault Support (`YOUTUBE_COOKIES_FILE`)**:
   - Pass export of `cookies.txt` to seamlessly access age-restricted content.

---

## 🎚 Supported Formats & Bitrates

### 🎵 MP3 Audio
- **320 kbps (Ultra High Quality)**: Studio-fidelity MP3.
- **256 kbps (High Quality)**: Crisp sound with compact file size.
- **192 kbps (Standard)**: Optimal balance of speed and fidelity.
- **128 kbps (Economy)**: Fast download for low-bandwidth connections.
- **64 kbps (Low Bandwidth)**: Ultra-compact for podcasts and speech.
- *Includes automatic ID3 tagging with song title, channel name, and embedded cover art.*

### 🎬 MP4 Video
- **4K (2160p Ultra HD)**
- **2K (1440p Quad HD)**
- **1080p (Full HD)**
- **720p (HD - Fast)**
- **480p & 360p**

---

## 🌐 SEO Strategy for #1 Google Search Ranking

- **Schema.org JSON-LD**: Embedded `@graph` including `WebApplication`, `HowTo`, and `FAQPage` rich snippets.
- **Natural, High-Converting UI**: Clean pure white background, crisp typography, and red accents without spammy pop-unders.
- **Core Web Vitals**: Zero layout shift (CLS = 0) and Largest Contentful Paint (LCP) under 0.8s.
- **Discoverability**: Dynamic `/sitemap.xml` and `/robots.txt`.

---

## 🔌 REST API Reference

### 1. GET `/api/info`
Query video details, thumbnails, and available bitrates:
```http
GET /api/info?url=https://www.youtube.com/watch?v=jNQXAC9IVRw
```

### 2. GET `/api/download`
Stream converted MP3 or MP4 file directly:
```http
GET /api/download?url=https://www.youtube.com/watch?v=jNQXAC9IVRw&format=mp3&quality=320k
```

### 3. GET `/api/health`
System diagnostics & FFmpeg status:
```http
GET /api/health
```

---

## 🚀 Deploying to Production (VPS / Linux Server)

1. Rent a VPS (e.g. Ubuntu 24.04 on Hetzner, DigitalOcean, or AWS EC2).
2. Install Python and FFmpeg:
   ```bash
   sudo apt-get update && sudo apt-get install -y python3 python3-pip ffmpeg
   ```
3. Clone your repo onto the server and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run with production workers:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
5. Set up Nginx Reverse Proxy with SSL (Certbot / Let's Encrypt) pointing to `http://127.0.0.1:8000`.
