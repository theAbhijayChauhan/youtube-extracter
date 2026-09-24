import os
import tempfile
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Temporary downloads directory
# Uses system temp directory (%TEMP% on Windows, /tmp on Linux/Docker) so no files clutter the project folder
CUSTOM_TEMP = os.getenv("CUSTOM_TEMP_DIR")
if CUSTOM_TEMP:
    DOWNLOADS_TEMP_DIR = Path(CUSTOM_TEMP)
else:
    DOWNLOADS_TEMP_DIR = Path(tempfile.gettempdir()) / "zenthyt_temp"

# Ensure temp directory exists
DOWNLOADS_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Application Branding & Settings
APP_TITLE = "ZenthYT - Fast YouTube to MP3 & MP4 Converter"
APP_DESCRIPTION = "High-speed, free YouTube to MP3 audio and MP4 video converter. Supports 320kbps studio MP3 and 4K MP4 downloads."
APP_VERSION = "1.0.0"

# Anti-Bot & Extractor Settings
# Rotate across multiple YouTube player clients to bypass BotGuard on cloud datacenter IPs
PLAYER_CLIENTS = ["tv", "ios", "android", "mweb", "web"]

# Proof-of-Origin (PO) Token support for YouTube BotGuard
YOUTUBE_PO_TOKEN = os.getenv("YOUTUBE_PO_TOKEN", "").strip() or None

# User Agents for realistic browser spoofing
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "com.google.android.youtube/19.16.39 (Linux; U; Android 14; US) gzip",
]

# Optional Proxy: HTTP / HTTPS / SOCKS5 proxy string (e.g. "http://user:pass@proxy.ip:port")
PROXY_URL = os.getenv("YOUTUBE_PROXY", "").strip() or None

# Automatic Cookies Resolution Hierarchy:
# 1. YOUTUBE_COOKIES_TEXT environment variable (directly paste cookiefile content on Render/Fly.io)
# 2. Render Secret File mounted at /etc/secrets/cookies.txt
# 3. YOUTUBE_COOKIES_FILE custom path environment variable
# 4. Local cookies.txt in project root directory
COOKIES_FILE = None

raw_cookie_text = os.getenv("YOUTUBE_COOKIES_TEXT", "").strip()
if raw_cookie_text:
    try:
        injected_cookies_path = DOWNLOADS_TEMP_DIR / "injected_cookies.txt"
        injected_cookies_path.write_text(raw_cookie_text, encoding="utf-8")
        COOKIES_FILE = str(injected_cookies_path)
    except Exception:
        pass

if not COOKIES_FILE:
    render_secret_cookies = Path("/etc/secrets/cookies.txt")
    custom_env_cookies = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
    local_cookies = BASE_DIR / "cookies.txt"

    if render_secret_cookies.exists():
        COOKIES_FILE = str(render_secret_cookies)
    elif custom_env_cookies and Path(custom_env_cookies).exists():
        COOKIES_FILE = custom_env_cookies
    elif local_cookies.exists():
        COOKIES_FILE = str(local_cookies)

# Performance & Streaming
STREAM_CHUNK_SIZE = 256 * 1024  # 256 KB chunks for high throughput
CACHE_TTL_SECONDS = 3600  # 1 Hour metadata caching
MAX_VIDEO_DURATION_SECONDS = 14400  # 4 hours max per video

# Server Host & Port
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
