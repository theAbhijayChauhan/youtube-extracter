import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional
import imageio_ffmpeg
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, ID3NoHeaderError
import requests

logger = logging.getLogger("yt_converter.ffmpeg")

def get_ffmpeg_binary() -> str:
    """Return absolute path to FFmpeg binary."""
    try:
        binary = imageio_ffmpeg.get_ffmpeg_exe()
        if binary and os.path.exists(binary):
            return binary
    except Exception as e:
        logger.warning(f"imageio_ffmpeg binary not found: {e}")

    # Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    raise RuntimeError("FFmpeg executable could not be located on the system.")

FFMPEG_EXE = get_ffmpeg_binary()

def inject_mp3_metadata(
    file_path: Path,
    title: str,
    artist: str,
    thumbnail_url: Optional[str] = None
) -> None:
    """Inject ID3 tags (Title, Artist, Album, and Thumbnail cover art) into MP3 file."""
    try:
        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        # Set text tags
        audio.tags["TIT2"] = TIT2(encoding=3, text=title)
        audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
        audio.tags["TALB"] = TALB(encoding=3, text="YouTube Audio Stream")

        # Download & embed cover artwork if thumbnail is present
        if thumbnail_url:
            try:
                resp = requests.get(thumbnail_url, timeout=5)
                if resp.status_code == 200:
                    audio.tags["APIC"] = APIC(
                        encoding=3,
                        mime="image/jpeg" if "jpg" in thumbnail_url.lower() or "jpeg" in thumbnail_url.lower() else "image/png",
                        type=3,  # Front cover
                        desc="Cover",
                        data=resp.content
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch thumbnail for ID3 tagging: {e}")

        audio.save()
    except Exception as e:
        logger.error(f"Error injecting MP3 metadata into {file_path}: {e}")

def run_ffmpeg_conversion(
    input_args: list,
    output_path: Path,
    extra_output_args: Optional[list] = None
) -> None:
    """Run an FFmpeg conversion command synchronously with timeout and error checking."""
    cmd = [FFMPEG_EXE, "-y"] + input_args
    if extra_output_args:
        cmd.extend(extra_output_args)
    cmd.append(str(output_path))

    logger.info(f"Executing FFmpeg: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600  # 10 min max timeout for heavy 4K muxing
    )

    if result.returncode != 0:
        error_msg = result.stderr.decode("utf-8", errors="ignore")
        logger.error(f"FFmpeg error: {error_msg}")
        raise RuntimeError(f"FFmpeg conversion failed: {error_msg[-500:]}")
