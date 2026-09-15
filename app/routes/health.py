import sys
from fastapi import APIRouter
import yt_dlp
from app.services.ffmpeg_engine import FFMPEG_EXE
from app.services.cache_engine import metadata_cache
from app.config import APP_VERSION

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health")
async def health_check():
    """Returns system status, FFmpeg configuration, and component health."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "python_version": sys.version.split()[0],
        "ytdlp_version": yt_dlp.version.__version__,
        "ffmpeg_path": FFMPEG_EXE,
        "cache_items": len(metadata_cache._cache),
    }
