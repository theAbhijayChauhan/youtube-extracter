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

def resolve_cookies_file() -> Optional[str]:
    """Resolve and validate the active cookies file path across all environments."""
    # 1. Environment Variable text (YOUTUBE_COOKIES_TEXT)
    raw_cookie_text = os.getenv("YOUTUBE_COOKIES_TEXT", "").strip()
    if raw_cookie_text:
        # Strip surrounding quotes if added by shell or UI
        if (raw_cookie_text.startswith('"') and raw_cookie_text.endswith('"')) or \
           (raw_cookie_text.startswith("'") and raw_cookie_text.endswith("'")):
            raw_cookie_text = raw_cookie_text[1:-1].strip()

        # Fix literal \n escaped strings from environment inputs
        if "\\n" in raw_cookie_text and "\n" not in raw_cookie_text:
            raw_cookie_text = raw_cookie_text.replace("\\n", "\n")

        # Base64 decoding support
        if not raw_cookie_text.startswith("#") and "Netscape" not in raw_cookie_text:
            try:
                import base64
                decoded = base64.b64decode(raw_cookie_text).decode("utf-8", errors="ignore")
                if "youtube.com" in decoded or "Netscape" in decoded:
                    raw_cookie_text = decoded
            except Exception:
                pass

        if raw_cookie_text:
            # Ensure Netscape header
            if not raw_cookie_text.startswith("# Netscape"):
                raw_cookie_text = "# Netscape HTTP Cookie File\n" + raw_cookie_text

            try:
                injected_path = DOWNLOADS_TEMP_DIR / "injected_cookies.txt"
                injected_path.write_text(raw_cookie_text, encoding="utf-8")
                return str(injected_path)
            except Exception:
                pass

    # 2. Render Secret File mounted at /etc/secrets/cookies.txt
    render_secret = Path("/etc/secrets/cookies.txt")
    if render_secret.exists() and render_secret.stat().st_size > 0:
        return str(render_secret)

    # 3. Custom path via YOUTUBE_COOKIES_FILE
    custom_path = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
    if custom_path and Path(custom_path).exists() and Path(custom_path).stat().st_size > 0:
        return custom_path

    # 4. Local cookies.txt in project root
    local_file = BASE_DIR / "cookies.txt"
    if local_file.exists() and local_file.stat().st_size > 0:
        return str(local_file)

    return None

def get_cookies_status() -> Dict[str, Any]:
    """Inspect current cookies status for diagnostics and health check."""
    path = resolve_cookies_file()
    if path and os.path.exists(path) and os.path.getsize(path) > 0:
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            cookie_count = sum(1 for line in lines if line.strip() and not line.startswith("#"))
            has_youtube = "youtube.com" in content
            
            source = "Render Secret File (/etc/secrets/cookies.txt)" if "/etc/secrets" in path else (
                "Render Env Var (YOUTUBE_COOKIES_TEXT)" if "injected_cookies" in path else (
                    "Local File (cookies.txt)" if "cookies.txt" in path else "Custom File Path"
                )
            )
            return {
                "active": True,
                "source": source,
                "cookie_count": cookie_count,
                "has_youtube_cookies": has_youtube,
            }
        except Exception:
            return {"active": True, "source": "file", "cookie_count": 0, "has_youtube_cookies": True}
    return {
        "active": False,
        "source": "None",
        "cookie_count": 0,
        "has_youtube_cookies": False,
    }

COOKIES_FILE = resolve_cookies_file()

# Performance & Streaming
STREAM_CHUNK_SIZE = 256 * 1024  # 256 KB chunks for high throughput
CACHE_TTL_SECONDS = 3600  # 1 Hour metadata caching
MAX_VIDEO_DURATION_SECONDS = 14400  # 4 hours max per video

# Server Host & Port
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
