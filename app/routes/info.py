from fastapi import APIRouter, HTTPException, Query
from app.schemas.video import VideoInfoResponse, VideoInfoRequest
from app.services.ytdlp_engine import fetch_video_info, extract_video_id
import logging

logger = logging.getLogger("yt_converter.routes.info")
router = APIRouter(prefix="/api", tags=["Video Information"])

@router.get("/info", response_model=VideoInfoResponse)
async def get_video_info_get(url: str = Query(..., description="YouTube video or shorts URL")):
    """Fetch video metadata, thumbnails, and available audio/video quality options."""
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="YouTube URL is required.")

    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid YouTube video, shorts, or music link."
        )

    try:
        info = await fetch_video_info(url.strip())
        return info
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error fetching info for URL {url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch video information: {str(e)}"
        )

@router.post("/info", response_model=VideoInfoResponse)
async def get_video_info_post(payload: VideoInfoRequest):
    """POST endpoint for fetching video info via JSON body."""
    return await get_video_info_get(url=payload.url)
