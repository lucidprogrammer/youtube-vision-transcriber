# Use official Python slim image for the base
FROM python:3.13-slim

# Install system dependencies (ffmpeg is required for video splitting)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies using uv into the system python
RUN /uv/bin/uv sync --no-dev --system

# Ensure the data directory exists
ENV YOUTUBE_MCP_BASE_DIR=/app/youtube_data
RUN mkdir -p $YOUTUBE_MCP_BASE_DIR

# Entry point uses the command defined in pyproject.toml
ENTRYPOINT ["youtube-vision-transcriber"]
CMD ["--server"]
