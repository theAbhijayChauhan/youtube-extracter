from typing import List, Optional
from pydantic import BaseModel, Field

class AudioQualityOption(BaseModel):
    bitrate: str = Field(..., description="Bitrate e.g. '320k', '256k', '192k', '128k', '64k'")
    label: str = Field(..., description="User friendly label e.g. '320 kbps (Ultra High Quality)'")
    approx_size_mb: Optional[float] = Field(None, description="Estimated file size in MB")
    recommended: bool = False

class VideoQualityOption(BaseModel):
    resolution: str = Field(..., description="Resolution e.g. '1080p', '720p', '480p', '360p', '4K'")
    height: int = Field(..., description="Video height in pixels e.g. 1080, 720")
    label: str = Field(..., description="User friendly label e.g. '1080p (Full HD - 60fps)'")
    fps: Optional[int] = None
    has_audio: bool = True
    approx_size_mb: Optional[float] = None
    recommended: bool = False

class VideoInfoResponse(BaseModel):
    id: str
    url: str
    title: str
    channel: str
    channel_url: Optional[str] = None
    duration_seconds: int
    duration_formatted: str
    thumbnail: str
    views: Optional[int] = None
    views_formatted: Optional[str] = None
    audio_formats: List[AudioQualityOption]
    video_formats: List[VideoQualityOption]

class VideoInfoRequest(BaseModel):
    url: str = Field(..., description="YouTube video, Shorts, or Music URL")

class DownloadRequest(BaseModel):
    url: str
    format_type: str = Field("mp3", description="'mp3' or 'mp4'")
    quality: str = Field("320k", description="Bitrate (e.g. '320k') or resolution (e.g. '1080p')")
