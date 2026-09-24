import os
import re
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import requests
import yt_dlp

from app.config import (
    BASE_DIR,
    PLAYER_CLIENTS,
    YOUTUBE_PO_TOKEN,
    USER_AGENTS,
    PROXY_URL,
    COOKIES_FILE,
    DOWNLOADS_TEMP_DIR,
    MAX_VIDEO_DURATION_SECONDS,
)
from app.schemas.video import (
    VideoInfoResponse,
    AudioQualityOption,
    VideoQualityOption,
)
from app.services.cache_engine import metadata_cache
from app.services.ffmpeg_engine import FFMPEG_EXE, inject_mp3_metadata

logger = logging.getLogger("yt_converter.ytdlp")

def sanitize_filename(name: str) -> str:
    """Clean filename of invalid characters."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:120] if clean else "download"

def format_duration(seconds: int) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_views(views: Optional[int]) -> str:
    """Format large view counts into user-friendly strings."""
    if not views:
        return "0 views"
    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f}B views"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M views"
    if views >= 1_000:
        return f"{views / 1_000:.1f}K views"
    return f"{views:,} views"

def normalize_youtube_url(url: str) -> str:
    """Ensure URL has proper scheme and is clean."""
    clean = url.strip()
    if re.match(r"^[0-9A-Za-z_-]{11}$", clean):
        return f"https://www.youtube.com/watch?v={clean}"
    if not clean.startswith("http://") and not clean.startswith("https://"):
        clean = f"https://{clean}"
    return clean

def extract_video_id(url: str) -> Optional[str]:
    """Extract 11-character YouTube video ID from various URL patterns."""
    clean = url.strip()
    if re.match(r"^[0-9A-Za-z_-]{11}$", clean):
        return clean
    patterns = [
        r"(?:v=|\/|vi=)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/live\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, clean)
        if match:
            return match.group(1)
    return None

def get_base_ydl_opts(custom_clients: Optional[List[str]] = None) -> Dict[str, Any]:
    """Build fast yt-dlp options with cookies, player client rotation, PO token, and ffmpeg path."""
    cookie_path = COOKIES_FILE if (COOKIES_FILE and os.path.exists(COOKIES_FILE)) else str(BASE_DIR / "cookies.txt")
    clients = custom_clients or PLAYER_CLIENTS

    extractor_args: Dict[str, Any] = {
        "youtube": {
            "player_client": clients,
        }
    }
    if YOUTUBE_PO_TOKEN:
        extractor_args["youtube"]["po_token"] = [YOUTUBE_PO_TOKEN]

    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_EXE,
        "socket_timeout": 12,
        "retries": 2,
        "extractor_args": extractor_args,
        "js_runtimes": {"node": {}},
        "http_headers": {
            "User-Agent": USER_AGENTS[0],
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    if cookie_path and os.path.exists(cookie_path):
        opts["cookiefile"] = cookie_path
        logger.info(f"Using cookiefile at {cookie_path}")
    else:
        logger.warning("No cookiefile detected. Running in unauthenticated mode.")

    if PROXY_URL:
        opts["proxy"] = PROXY_URL
        logger.info(f"Using proxy: {PROXY_URL}")

    return opts

def _fetch_via_oembed(url: str, video_id: str) -> Dict[str, Any]:
    """Fallback fetch via official YouTube oEmbed API."""
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    logger.info(f"Attempting oEmbed metadata fetch for {video_id}")
    resp = requests.get(oembed_url, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        return {
            "id": video_id,
            "title": data.get("title", "YouTube Video"),
            "uploader": data.get("author_name", "YouTube Channel"),
            "thumbnail": data.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "duration": 210, # fallback estimation
            "view_count": None,
            "formats": []
        }
    raise RuntimeError(f"oEmbed fetch failed with status code {resp.status_code}")

def _extract_info_with_fallback(url: str) -> Dict[str, Any]:
    """Fast extraction using yt-dlp with client rotation and instant oEmbed fallback."""
    norm_url = normalize_youtube_url(url)
    clean_id = extract_video_id(url)
    last_exception = None

    # 1. Primary attempt: Base client rotation with cookies/node
    try:
        ydl_opts = get_base_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(norm_url, download=False)
            if info:
                return info
    except Exception as e:
        logger.warning(f"yt-dlp primary extraction error: {e}")
        last_exception = e

    # 2. Fast secondary attempt: Android client
    try:
        logger.info("Retrying extraction with Android client...")
        ydl_opts = get_base_ydl_opts(custom_clients=["android", "web"])
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(norm_url, download=False)
            if info:
                return info
    except Exception as e:
        logger.warning(f"yt-dlp Android fallback error: {e}")
        last_exception = e

    # 3. Fast oEmbed fallback for metadata preview
    if clean_id:
        try:
            return _fetch_via_oembed(norm_url, clean_id)
        except Exception as oembed_err:
            logger.error(f"oEmbed fallback error: {oembed_err}")

    err_msg = str(last_exception or "Video not available")
    if "Sign in to confirm" in err_msg:
        raise RuntimeError(
            "YouTube BotGuard challenge triggered on this cloud server IP. "
            "To fix: Paste your cookies.txt into Render as the 'YOUTUBE_COOKIES_TEXT' environment variable."
        )

    raise RuntimeError(f"Unable to fetch video information from YouTube: {err_msg}")

async def fetch_video_info(url: str) -> VideoInfoResponse:
    """Fetch video metadata and return formatted response."""
    clean_id = extract_video_id(url)
    cache_key = f"info:{clean_id or url}"

    cached = metadata_cache.get(cache_key)
    if cached:
        logger.info(f"Returning cached metadata for {cache_key}")
        return cached

    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(None, _extract_info_with_fallback, url)

    duration = int(info.get("duration", 0) or 0)
    if duration > MAX_VIDEO_DURATION_SECONDS:
        raise ValueError(
            f"Video duration ({format_duration(duration)}) exceeds maximum allowed length ({format_duration(MAX_VIDEO_DURATION_SECONDS)})."
        )

    title = info.get("title", "Unknown Title")
    channel = info.get("uploader", info.get("channel", "Unknown Channel"))
    thumbnail = info.get("thumbnail") or f"https://i.ytimg.com/vi/{info.get('id', clean_id or '')}/hqdefault.jpg"
    views = info.get("view_count")

    # Generate Audio Quality Options
    audio_bitrates = [
        ("320k", "320 kbps (Ultra High Quality - MP3)", True),
        ("256k", "256 kbps (High Quality - MP3)", False),
        ("192k", "192 kbps (Standard Quality - MP3)", False),
        ("128k", "128 kbps (Economy - Fast - MP3)", False),
        ("64k", "64 kbps (Low Bandwidth - MP3)", False),
    ]
    audio_formats: List[AudioQualityOption] = []
    for br, label, rec in audio_bitrates:
        br_num = int(br.replace("k", ""))
        approx_size = round((duration * br_num * 1000) / (8 * 1024 * 1024), 2) if duration else None
        audio_formats.append(
            AudioQualityOption(
                bitrate=br,
                label=label,
                approx_size_mb=approx_size,
                recommended=rec
            )
        )

    # Standard video resolutions
    sorted_heights = [2160, 1440, 1080, 720, 480, 360]
    height_labels = {
        2160: "4K (2160p Ultra HD)",
        1440: "2K (1440p Quad HD)",
        1080: "1080p (Full HD)",
        720: "720p (HD - Fast)",
        480: "480p (Standard Definition)",
        360: "360p (Data Saver)",
    }

    video_formats: List[VideoQualityOption] = []
    for h in sorted_heights:
        is_rec = (h == 1080)
        bitrate_est = {2160: 15000, 1440: 8000, 1080: 4500, 720: 2500, 480: 1200, 360: 700}.get(h, 2000)
        approx_size = round((duration * bitrate_est * 1000) / (8 * 1024 * 1024), 2) if duration else None

        video_formats.append(
            VideoQualityOption(
                resolution=f"{h}p" if h <= 1080 else ("4K" if h == 2160 else "2K"),
                height=h,
                label=height_labels.get(h, f"{h}p"),
                fps=60 if h >= 1080 else 30,
                has_audio=True,
                approx_size_mb=approx_size,
                recommended=is_rec
            )
        )

    response = VideoInfoResponse(
        id=info.get("id", clean_id or "unknown"),
        url=f"https://www.youtube.com/watch?v={info.get('id', clean_id or '')}",
        title=title,
        channel=channel,
        channel_url=info.get("uploader_url") or info.get("channel_url"),
        duration_seconds=duration,
        duration_formatted=format_duration(duration),
        thumbnail=thumbnail,
        views=views,
        views_formatted=format_views(views),
        audio_formats=audio_formats,
        video_formats=video_formats,
    )

    metadata_cache.set(cache_key, response, ttl=3600)
    return response

async def process_and_download(
    url: str,
    format_type: str,
    quality: str
) -> Tuple[Path, str, str]:
    """Download and convert video or audio to local temp file with custom quality and metadata."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_download, url, format_type, quality)

def _download_media_with_fallback(base_opts: Dict[str, Any], url: str) -> None:
    """Download media with fast fallback for cloud datacenter environments."""
    try:
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            ydl.download([url])
            return
    except Exception as e:
        err_msg = str(e)
        if "Sign in to confirm" in err_msg or "Failed to extract" in err_msg:
            logger.warning("Bot challenge during download. Retrying with Android client...")
            retry_opts = dict(base_opts)
            retry_opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            }
            try:
                with yt_dlp.YoutubeDL(retry_opts) as ydl:
                    ydl.download([url])
                    return
            except Exception as e2:
                logger.error(f"Fallback download error: {e2}")
                raise RuntimeError(
                    "YouTube BotGuard blocked this datacenter IP during download. "
                    "To fix: Paste your cookies.txt into Render as the 'YOUTUBE_COOKIES_TEXT' environment variable."
                )
        raise

def _sync_download(
    url: str,
    format_type: str,
    quality: str
) -> Tuple[Path, str, str]:
    """Synchronous worker that invokes yt-dlp & FFmpeg pipeline."""
    norm_url = normalize_youtube_url(url)
    job_id = uuid.uuid4().hex[:10]
    out_dir = DOWNLOADS_TEMP_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    info = _extract_info_with_fallback(norm_url)
    raw_title = info.get("title", "download")
    safe_title = sanitize_filename(raw_title)
    artist = info.get("uploader", info.get("channel", "YouTube Artist"))
    thumbnail = info.get("thumbnail")

    ydl_opts = get_base_ydl_opts()

    if format_type.lower() == "mp3":
        bitrate_val = quality.lower().replace("k", "")
        if not bitrate_val.isdigit():
            bitrate_val = "320"

        filename = f"{safe_title}.mp3"
        out_template = str(out_dir / "%(id)s.%(ext)s")

        ydl_opts.update({
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate_val,
                }
            ],
            "prefer_ffmpeg": True,
            "keepvideo": False,
        })

        _download_media_with_fallback(ydl_opts, norm_url)

        generated_files = list(out_dir.glob("*.mp3"))
        if not generated_files:
            raise RuntimeError("Audio conversion failed: MP3 output was not created.")

        output_file = generated_files[0]

        inject_mp3_metadata(
            file_path=output_file,
            title=raw_title,
            artist=artist,
            thumbnail_url=thumbnail
        )

        return output_file, filename, "audio/mpeg"

    else:
        filename = f"{safe_title}.mp4"
        out_template = str(out_dir / "%(id)s.%(ext)s")

        height_str = quality.lower().replace("p", "").replace("k", "")
        if height_str == "4":
            height_target = 2160
        elif height_str == "2":
            height_target = 1440
        elif height_str.isdigit():
            height_target = int(height_str)
        else:
            height_target = 1080

        format_selector = (
            f"bestvideo[height<={height_target}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height_target}]+bestaudio/"
            f"best[height<={height_target}][ext=mp4]/"
            f"best"
        )

        ydl_opts.update({
            "format": format_selector,
            "outtmpl": out_template,
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            "prefer_ffmpeg": True,
        })

        _download_media_with_fallback(ydl_opts, norm_url)

        generated_files = list(out_dir.glob("*.mp4"))
        if not generated_files:
            all_files = list(out_dir.glob("*.*"))
            if all_files:
                output_file = all_files[0]
            else:
                raise RuntimeError("Video download failed: Output file was not created.")
        else:
            output_file = generated_files[0]

        return output_file, filename, "video/mp4"
