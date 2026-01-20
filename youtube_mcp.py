from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Initialize logger
logger = logging.getLogger(__name__)

mcp = FastMCP(name="YouTubeVisionTranscriber")


def get_base_dir() -> Path:
    """
    Get the base directory for storing YouTube video data.
    
    Returns:
        Path: The absolute path to the data directory.
        
    Examples:
        >>> str(get_base_dir()).endswith("youtube_data")
        True
    """
    base = os.environ.get("YOUTUBE_MCP_BASE_DIR", "./youtube_data")
    p = Path(base).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def slugify(title: str) -> str:
    """
    Create a Linux-safe slug from a video title.
    - lowercase
    - keep alnum, dash
    - spaces -> dash
    - strip leading/trailing dashes
    - append 4-char MD5 hash of original title for collision resistance
    
    Args:
        title: The original video title.
        
    Returns:
        str: A slugified string suitable for filenames.
    """
    clean_title = title.strip().lower()
    # replace @, (), etc. with space then normalize
    clean_title = re.sub(r"[^a-z0-9]+", "-", clean_title)
    clean_title = re.sub(r"-+", "-", clean_title)
    base_slug = clean_title.strip("-") or "video"
    
    # 4 char hash of original title for collision resistance
    hash_suffix = hashlib.md5(title.encode("utf-8")).hexdigest()[:4]
    
    return f"{base_slug}-{hash_suffix}"

# --------- ffprobe / ffmpeg helpers ---------


def run_cmd(args: list[str]) -> None:
    """Run a shell command and check for errors."""
    proc = subprocess.run(
        args,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    logger.info("Command %s output:\n%s", " ".join(args), proc.stdout)

def probe_duration(input_path: Path) -> float:
    """
    Return video duration in seconds using ffprobe.
    
    Args:
        input_path: Path to the video file.
        
    Returns:
        float: Duration in seconds.
    """
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())

def get_file_size_mb(path: Path) -> float:
    """Return file size in MB."""
    return path.stat().st_size / (1024 * 1024)

# --------- manifest model ---------

@dataclass
class PartInfo:
    index: int
    filename: str
    size_mb: float
    start_seconds: float
    end_seconds: float

@dataclass
class VideoManifest:
    slug: str
    title: str
    youtube_url: str
    base_dir: str
    original_video: str
    part_size_mb: int
    parts: list[PartInfo]

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "youtube_url": self.youtube_url,
            "base_dir": self.base_dir,
            "original_video": self.original_video,
            "part_size_mb": self.part_size_mb,
            "parts": [asdict(p) for p in self.parts],
        }

# --------- core logic (non-MCP) ---------

def download_youtube(url: str, slug: str | None, video_dir: Path) -> Path:
    """
    Use yt-dlp to download video as mp4.
    
    Args:
        url: YouTube video URL.
        slug: Video slug for naming.
        video_dir: Target directory.
        
    Returns:
        Path: Path to the downloaded .mp4 file.
    """
    video_dir.mkdir(parents=True, exist_ok=True)
    
    filename_base = slug if slug else "original"
    output_tmpl = str(video_dir / f"{filename_base}.%(ext)s")

    run_cmd([
        "yt-dlp",
        "-f", "mp4",
        "-o", output_tmpl,
        url,
    ])

    # find downloaded file
    candidates = list(video_dir.glob(f"{filename_base}.*"))
    if not candidates:
        raise RuntimeError(f"Download failed: no {filename_base}.* file")
    # pick first
    downloaded = candidates[0]
    # normalize to .mp4 if needed
    if downloaded.suffix != ".mp4":
        target = video_dir / f"{filename_base}.mp4"
        downloaded.rename(target)
        return target
    return downloaded

def split_video_into_parts(
    video_path: Path,
    slug: str,
    part_mb: int,
) -> list[PartInfo]:
    """
    Split video into chunks of approximately part_mb.
    
    Args:
        video_path: Path to the source video.
        slug: Video slug.
        part_mb: Target size for each part in MB.
        
    Returns:
        list[PartInfo]: List of created video parts.
    """
    parts_dir = video_path.parent / "parts"
    parts_dir.mkdir(exist_ok=True)

    total_size_mb = get_file_size_mb(video_path)
    duration = probe_duration(video_path)

    if total_size_mb <= part_mb:
        # No need to split
        out_path = parts_dir / f"{slug}_part_000.mp4"
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-c", "copy",
            str(out_path),
        ])
        size_mb = get_file_size_mb(out_path)
        return [PartInfo(0, out_path.name, size_mb, 0.0, duration)]

    # naive proportional split: assume constant bitrate
    num_parts = math.ceil(total_size_mb / part_mb)
    segment_time = duration / num_parts

    pattern = str(parts_dir / f"{slug}_part_%03d.mp4")

    run_cmd([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", str(segment_time),
        pattern,
    ])

    part_files = sorted(parts_dir.glob(f"{slug}_part_*.mp4"))
    parts: list[PartInfo] = []
    for idx, f in enumerate(part_files):
        size_mb = get_file_size_mb(f)
        start = idx * segment_time
        end = min(duration, (idx + 1) * segment_time)
        parts.append(
            PartInfo(
                index=idx,
                filename=f.name,
                size_mb=round(size_mb, 2),
                start_seconds=round(start, 2),
                end_seconds=round(end, 2),
            )
        )
    return parts

def write_manifest(
    manifest: VideoManifest,
    video_dir: Path,
) -> None:
    """Write the video manifest to disk."""
    path = video_dir / "manifest.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2)

def load_manifest(slug: str) -> VideoManifest:
    """
    Load a video manifest by slug.
    
    Args:
        slug: The video identifier.
        
    Returns:
        VideoManifest: The loaded manifest.
        
    Raises:
        FileNotFoundError: If manifest doesn't exist.
    """
    base_dir = get_base_dir()
    video_dir = base_dir / slug
    path = video_dir / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found for slug {slug}")
    data = json.loads(path.read_text(encoding="utf-8"))
    parts = [
        PartInfo(**p_dict) for p_dict in data.get("parts", [])
    ]
    return VideoManifest(
        slug=data["slug"],
        title=data["title"],
        youtube_url=data["youtube_url"],
        base_dir=data["base_dir"],
        original_video=data["original_video"],
        part_size_mb=data["part_size_mb"],
        parts=parts,
    )

# --------- MCP tools ---------

@mcp.tool
def prepare_youtube_video(
    url: str,
    part_mb: int = 15,
) -> dict:
    """
    Download a YouTube video, normalize the filename, split into parts.
    
    Args:
        url: The YouTube URL.
        part_mb: Target size for video parts in MB.
        
    Returns:
        dict: Processed video metadata including resources.
    """
    try:
        base_dir = get_base_dir()

        # 1) Get title via yt-dlp JSON
        meta = subprocess.run(
            ["yt-dlp", "-J", url],
            check=True,
            capture_output=True,
            text=True,
        )
        meta_json = json.loads(meta.stdout)
        title = meta_json.get("title") or "youtube-video"
        slug = slugify(title)

        video_dir = base_dir / slug

        # 2) download
        video_path = download_youtube(url, slug, video_dir)

        # 3) split
        parts = split_video_into_parts(video_path, slug, part_mb=part_mb)

        # 4) write manifest
        manifest = VideoManifest(
            slug=slug,
            title=title,
            youtube_url=url,
            base_dir=str(video_dir),
            original_video=video_path.name,
            part_size_mb=part_mb,
            parts=parts,
        )
        write_manifest(manifest, video_dir)

        parts_resources = [
            f"video://{slug}/part/{p.index}" for p in parts
        ]
        return {
            "slug": slug,
            "title": title,
            "youtube_url": url,
            "base_dir": str(video_dir),
            "parts": [asdict(p) for p in parts],
            "manifest_resource": f"video://{slug}/manifest",
            "parts_resources": parts_resources,
        }
    except Exception as e:
         logger.error(f"Preparation failed: {str(e)}")
         raise

# --------- MCP resources ---------

@mcp.resource("video://{slug}/manifest")
def video_manifest(slug: str) -> dict:
    """Return the manifest JSON for a given video slug."""
    manifest = load_manifest(slug)
    return manifest.to_dict()

@mcp.resource("video://{slug}/part/{index}")
def video_part(slug: str, index: int) -> dict:
    """Return metadata for a single video part."""
    manifest = load_manifest(slug)
    for p in manifest.parts:
        if p.index == index:
            d = asdict(p)
            d["file_path"] = str(
                Path(manifest.base_dir) / "parts" / p.filename
            )
            return d
    raise ValueError(f"No part {index} for slug {slug}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        import doctest
        doctest.testmod(verbose=True)    
    else:
        mcp.run(transport="stdio")
