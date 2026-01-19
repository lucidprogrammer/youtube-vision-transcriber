# YouTube Vision Transcriber

**AI-powered pipeline that converts YouTube videos into polished articles using vision-based transcription.**

Unlike standard transcribers that only read audio captions, this tool uses **Google Gemini 2.0 Flash** (via `fast-agent`) to "watch" the video, capturing code snippets, terminal output, and on-screen text that subtitles often miss.

## Features

- **Vision-Based Transcription**: Captures visual context, code blocks, and diagrams.
- **MCP-Native**: Built with the [Model Context Protocol](https://modelcontextprotocol.io), compatible with Claude Desktop and VS Code.
- **Robust Pipeline**:
    - **Video Preparer**: Downloads and splits videos into manageable chunks.
    - **Part Transcriber**: Transcribes each chunk with timestamped visual details.
    - **Doc Writer**: Synthesizes a structured technical article from the transcript.
- **Fast & Efficient**: Uses `uv` for dependency management and `fast-agent` for orchestration.

## Prerequisites

- **Python**: >= 3.13.5
- **uv**: [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **API Keys**:
    - **Google Gemini**: For vision transcription.
    - **OpenAI** (Optional): For orchestration (default model is `gpt-4o-mini`, but can be changed).

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/lucidprogrammer/youtube-vision-transcriber.git
    cd youtube-vision-transcriber
    ```

2.  **Install dependencies**:
    ```bash
    uv sync
    ```

3.  **Configure API Keys**:
    Copy the example secrets file and edit it:
    ```bash
    cp fastagent.secrets.yaml.example fastagent.secrets.yaml
    ```
    Add your API keys to `fastagent.secrets.yaml`:
    ```yaml
    google:
      api_key: "YOUR_GEMINI_API_KEY"
    openai:
      api_key: "YOUR_OPENAI_API_KEY"
    ```

## CLI Usage

You can run the agent interactively in your terminal:

```bash
uv run agent.py
```

Paste a YouTube URL when prompted. The agent will:
1.  Download the video to `./youtube_data`.
2.  Split and transcribe it.
3.  Generate an `article.md` in the video's folder.

## Quick Start (Docker)

The easiest way to use this tool is via its official Docker image. No installation required other than Docker.

```bash
docker run -it --rm \
  -e GOOGLE__API_KEY="your_google_key" \
  -e OPENAI__API_KEY="your_openai_key" \
  -v /absolute/path/to/data:/app/youtube_data \
  lucidprogrammer/youtube-vision-transcriber
```

## Environment Configuration

Configuration is provided through environment variables using the `SECTION__SUBSECTION__PROPERTY` pattern:

- `GOOGLE__API_KEY`: Your Google Gemini API Key.
- `OPENAI__API_KEY`: Your OpenAI API Key (Optional, defaults to GPT-4o-mini).
- `YOUTUBE_MCP_BASE_DIR`: Path inside the container (`/app/youtube_data`). **Always map this to a local volume** to persist video data.

## MCP Client Usage

You can use this tool directly in **Claude Desktop** or **VS Code** by pointing to the Docker image.

### VS Code (MCP Extension) / Claude Desktop

Add the following to your configuration:

```json
{
  "mcpServers": {
    "youtube-vision": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "GOOGLE__API_KEY=your_google_key",
        "-e", "OPENAI__API_KEY=your_openai_key",
        "-v", "/absolute/path/to/data_dir:/app/youtube_data",
        "lucidprogrammer/youtube-vision-transcriber"
      ]
    }
  }
}
```

## Architecture

The system consists of three main MCP components orchestrated by a master agent:

1.  **YouTubeVisionTranscriber (`youtube_mcp.py`)**: Handles downloading (`yt-dlp`) and splitting videos (`ffmpeg`).
2.  **VideoTranscriberServer (`video_transcriber_mcp.py`)**: Wraps internal LLM calls to process video chunks.
3.  **Filessytem Server**: Manages reading/writing data to `./youtube_data`.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
