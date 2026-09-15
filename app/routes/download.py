import os
import re
import shutil
import urllib.parse
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import aiofiles

from app.services.ytdlp_engine import process_and_download, extract_video_id
from app.config import STREAM_CHUNK_SIZE

logger = logging.getLogger("yt_converter.routes.download")
router = APIRouter(prefix="/api", tags=["Download"])

async def file_streamer(file_path: Path, chunk_size: int = STREAM_CHUNK_SIZE):
    """Async generator to stream file chunks to the HTTP response."""
    try:
        async with aiofiles.open(file_path, mode="rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        logger.error(f"Error streaming file {file_path}: {e}")
        raise

def cleanup_job_folder(folder_path: Path):
    """Background task to remove temporary download folder after response completes."""
    try:
        if folder_path.exists() and folder_path.is_dir():
            shutil.rmtree(folder_path, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory {folder_path}")
    except Exception as e:
        logger.warning(f"Error cleaning up directory {folder_path}: {e}")

@router.get("/download")
async def download_media_endpoint(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube video or shorts URL"),
    format: str = Query("mp3", description="Format type: 'mp3' or 'mp4'"),
    quality: str = Query("320k", description="Quality: '320k', '256k', '192k', '128k', '1080p', '720p', etc.")
):
    """
    Download and convert video or audio to requested format and stream directly to client.
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="YouTube URL is required.")

    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL.")

    format_type = format.lower().strip()
    if format_type not in ["mp3", "mp4"]:
        raise HTTPException(status_code=400, detail="Unsupported format. Choose 'mp3' or 'mp4'.")

    try:
        # Process and download the media
        file_path, filename, media_type = await process_and_download(
            url=url.strip(),
            format_type=format_type,
            quality=quality.strip()
        )

        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Converted file could not be found.")

        file_size = os.path.getsize(file_path)
        job_dir = file_path.parent

        # Register cleanup background task once the stream finishes
        background_tasks.add_task(cleanup_job_folder, job_dir)

        # Encode filename for RFC 5987 / RFC 6266 Content-Disposition compatibility
        # 1. UTF-8 percent-encoded filename (preserves full international Unicode titles: Hindi, Japanese, Arabic, etc.)
        encoded_filename = urllib.parse.quote(filename, encoding="utf-8")

        # 2. Strict ASCII-only fallback string for HTTP header latin-1 compliance (prevents UnicodeEncodeError)
        ascii_fallback = re.sub(r"[^\x20-\x7E]", "", filename).strip()
        ascii_fallback = ascii_fallback.replace('"', '').replace('\\', '').strip()
        if not ascii_fallback or ascii_fallback.startswith("."):
            ascii_fallback = f"zenthyt_{video_id}.{format_type}"

        headers = {
            "Content-Disposition": f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_filename}',
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }

        return StreamingResponse(
            file_streamer(file_path),
            media_type=media_type,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Download conversion error for {url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Conversion error: {str(e)}"
        )
