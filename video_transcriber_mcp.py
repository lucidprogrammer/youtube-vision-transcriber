"""Video Transcriber MCP Server

Exposes transcriber tool that receives video file paths and transcribes them.
"""

import asyncio
import base64
import mimetypes
from pathlib import Path

from fast_agent import FastAgent
import logging
import os
import traceback

# Setup persistent logging to a file that lives on the host volume
base_dir = os.environ.get("YOUTUBE_MCP_BASE_DIR", "./youtube_data")
log_path = Path(base_dir).resolve() / "video_subserver.log"
logging.basicConfig(
    filename=str(log_path),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("VideoTranscriberServer")

# Initialize FastMCP server
mcp = FastMCP(name="VideoTranscriberServer")

# Initialize FastAgent for LLM capabilities
fast = FastAgent("InternalTranscriber")

# Define helper agent
@fast.agent(
    name="internal_transcriber",
    instruction="INTERNAL USE ONLY - DO NOT USE THIS AGENT DIRECTLY.",
    model="google.gemini-2.0-flash"
)
async def internal_transcriber_func():
    pass

@mcp.tool
async def transcribe_video_file(video_path_str: str) -> str:
    """
    Transcribe a local video file using an internal multimodal agent.

    Args:
        video_path_str: The absolute path to the local video file.

    Returns:
        str: The generated transcript or an error message prefixed with "Error:".
    """
    video_path = Path(video_path_str.strip())
    
    logger.info(f"Processing video: {video_path}")

    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return f"Error: File not found at {video_path}"

    # Read and encode video
    try:
        video_bytes = video_path.read_bytes()
        blob_b64 = base64.b64encode(video_bytes).decode("utf-8")
        
        # Detect mime type manually for common video formats to be safe
        suffix = video_path.suffix.lower()
        if suffix == ".webm":
            mime_type = "video/webm"
        elif suffix == ".mp4":
            mime_type = "video/mp4"
        else:
            mime_type, _ = mimetypes.guess_type(video_path)
            if not mime_type:
                mime_type = "video/mp4" # Fallback

        # Construct Multimodal Message
        resource = EmbeddedResource(
            type="resource",
            resource=BlobResourceContents(
                blob=blob_b64,
                mimeType=mime_type,
                uri=video_path.as_uri()
            )
        )
        
        prompt_message = PromptMessageExtended(
            role="user",
            content=[
                text_content(f"Transcribe this video file: {video_path.name}. Provide a detailed timestamped transcript."),
                resource
            ]
        )

        async with fast.run() as app_ctx:
             llm = app_ctx.internal_transcriber.llm
             
             result = await llm.generate(
                 [prompt_message],
                 request_params=RequestParams(
                     systemPrompt="You are an expert video transcriber. Provide a detailed timestamped transcript of the video provided.",
                     maxTokens=8192
                 )
             )
             return result.last_text()
             
    except Exception as e:
         error_trace = traceback.format_exc()
         logger.error(f"Transcription failed: {str(e)}\n{error_trace}")
         return f"Error: {str(e)}"

if __name__ == "__main__":
    # Use mcp.run() with stdio transport
    mcp.run(transport="stdio")
