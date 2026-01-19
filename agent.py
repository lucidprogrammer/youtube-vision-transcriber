"""
YouTube Vision Transcriber Agent

Uses fast-agent chain pattern:
- video_preparer: Downloads YouTube video and splits into parts (MCP)
- part_transcriber: Transcribes video parts using Gemini vision via MCP
- doc_writer: Creates polished article from transcript
"""

import asyncio
import os
from pathlib import Path

from fast_agent import FastAgent

fast = FastAgent("YouTubeVisionTranscriber")

def get_base_dir() -> Path:
    """Get the base data directory from env or default."""
    base = os.environ.get("YOUTUBE_MCP_BASE_DIR", "./youtube_data")
    path = Path(base).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


# 1) Video preparer - downloads and splits via youtube_vision_transcriber MCP
@fast.agent(
    name="video_preparer",
    instruction="""You prepare YouTube videos for transcription.
When given a YouTube URL, call the `prepare_youtube_video` tool.

Return the JSON with these fields that the next agent needs:
- base_dir: the full path to the video folder
- parts: array with each part's index and filename

The next agent will construct paths like: {base_dir}/parts/{filename}""",
    servers=["youtube_vision_transcriber"],
)


# 2) Part transcriber - transcribes each part via video_transcriber_server MCP
@fast.agent(
    name="part_transcriber",
    instruction="""You are a transcription orchestrator.

Given the manifest/parts info from video_preparer:

1. For each part in the parts list:
   - Get the full video path: {base_dir}/parts/{filename}
   - Call the `transcribe_video_file` tool with that full path
   - Save the transcript to {base_dir}/transcripts/part_{index}.json

2. After all parts are transcribed, combine them into one chronological transcript.

3. Output the combined transcript.
4. IMPORTANT: At the very end of your response, output a separate line: "Base Directory: {base_dir}"

Example: If base_dir is "/path/to/youtube_data/my-video" and filename is "my-video_part_000.mp4",
call transcribe_video_file with "/path/to/youtube_data/my-video/parts/my-video_part_000.mp4".""",
    servers=["video_transcriber_server", "filesystem"],
)


# 3) Doc writer - creates polished article
@fast.agent(
    name="doc_writer",
    instruction="""You are a technical writer.

Given a detailed transcript of a tutorial video:
- Organize it into a clear, structured written tutorial.
- Use headings, bullet points, and fenced code blocks.
- Preserve commands and code exactly.
- Include a short intro and a recap section at the end.
- Look for the "Base Directory: ..." line at the end of the transcript.
- Save the article to {base_dir}/article.md using that path.""",
    servers=["filesystem"],
)


# 4) Chain: youtube_to_article
@fast.chain(
    name="youtube_to_article",
    sequence=["video_preparer", "part_transcriber", "doc_writer"],
    default=True,
)


async def main():
    """Run in interactive mode with youtube_to_article as default."""
    get_base_dir() # Ensure directory exists
    async with fast.run() as agent:
        await agent.interactive()


async def run_server():
    """Run as MCP server exposing youtube_to_article tool."""
    get_base_dir() # Ensure directory exists
    await fast.start_server(
        transport="stdio",
        server_name="youtube_vision_transcriber",
        server_description="Convert YouTube videos to polished articles. Send a YouTube URL to get a detailed article.",
        tool_description="Send a YouTube URL to transcribe and convert to an article. Returns the path to the generated article.",
    )

def start_server():
    """Entry point for project script (uvx support)."""
    asyncio.run(run_server())

if __name__ == "__main__":
    import sys
    
    if "--server" in sys.argv:
        # Run as MCP server
        asyncio.run(run_server())
    else:
        # Run interactively
        asyncio.run(main())

