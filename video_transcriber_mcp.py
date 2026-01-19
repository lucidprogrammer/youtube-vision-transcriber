"""Video Transcriber MCP Server

Exposes transcriber tool that receives video file paths and transcribes them.
"""

import asyncio
import base64
from pathlib import Path
import mimetypes
import sys
import logging

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from fast_agent import FastAgent
from fast_agent.types import PromptMessageExtended, text_content, RequestParams
from mcp.types import BlobResourceContents, EmbeddedResource

# Initialize FastMCP server
mcp = FastMCP(name="VideoTranscriberServer")

# Initialize FastAgent for LLM capabilities
fast = FastAgent("InternalTranscriber")

# Define helper agent
@fast.agent(
    name="internal_transcriber",
    instruction="INTERNAL USE ONLY - DO NOT USE THIS AGENT DIRECTLY.",
    model="google.gemini-2.5-flash"
)
async def internal_transcriber_func():
    pass

@mcp.tool
async def transcribe_video_file(video_path_str: str) -> str:
    """
    Transcribes a local video file.

    Args:
        video_path_str: The absolute path to the local video file.
    """
    video_path = Path(video_path_str.strip())
    
    # Log to file for reliable debugging
    with open("/tmp/video_debug.log", "a") as debug_file:
        debug_file.write(f"DEBUG: Processing {video_path}\n")

    if not video_path.exists():
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
         with open("/tmp/video_debug.log", "a") as debug_file:
            debug_file.write(f"ERROR: {str(e)}\n")
         return f"Error: {str(e)}"

if __name__ == "__main__":
    # Use mcp.run() with stdio transport
    mcp.run(transport="stdio")
