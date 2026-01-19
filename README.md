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

### 🚀 Quick Start (Docker)

1. **Pre-create a Persistent Volume** (Recommended for data persistence):
   ```bash
   # Create a Docker volume linked to your home folder for easy results access
   mkdir -p ~/youtube_data
   docker volume rm youtube_vision_vol || true
   docker volume create --driver local \
     --opt type=none \
     --opt device=$HOME/youtube_data \
     --opt o=bind \
     youtube_vision_vol
   ```

2. **Configure MCP Client**:
   Add this to your `windsurf.json`, `cursor.json`, or `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube-vision": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "GOOGLE__API_KEY=your_key_here",
        "-e", "OPENAI__API_KEY=your_key_here",
        "-v", "youtube_vision_vol:/app/youtube_data",
        "lucidprogrammer/youtube-vision-transcriber"
      ]
    }
  }
}
```

### 🛠️ Troubleshooting (Docker Mounts)

If you see a **"mounts denied"** error (e.g., `The path /tmp/youtube_data is not shared`):

1. **Host Sharing**: In Docker Desktop settings, go to **Resources > File Sharing** and ensure the path is added.
2. **Path Selection**: Use a path inside your home directory (e.g., `/Users/yourname/youtube_data`) which is usually shared by default.
3. **Absolute Paths**: Ensure you use the full absolute path on the host machine.

## Architecture

The system consists of three main MCP components orchestrated by a master agent:

1.  **YouTubeVisionTranscriber (`youtube_mcp.py`)**: Handles downloading (`yt-dlp`) and splitting videos (`ffmpeg`).
2.  **VideoTranscriberServer (`video_transcriber_mcp.py`)**: Wraps internal LLM calls to process video chunks.
3.  **Filessytem Server**: Manages reading/writing data to `./youtube_data`.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
