# Use official Python slim image for the base
FROM python:3.13-slim

ARG UV_VERSION=0.9.8

ENV PATH="/root/.local/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Upgrade nodejs and install system dependencies
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
      ca-certificates \
      curl \
      git \
      build-essential \
      ffmpeg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management using the official script
RUN curl -fsSL https://astral.sh/uv/${UV_VERSION}/install.sh | sh

# Pre-install the filesystem and fetch MCP servers globally to avoid runtime download timeouts
RUN npm install -g @modelcontextprotocol/server-filesystem
RUN uv pip install --system mcp-server-fetch

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies and the project itself using uv into the system python
RUN uv pip install --system .

# Ensure the data directory exists
ENV YOUTUBE_MCP_BASE_DIR=/app/youtube_data
RUN mkdir -p $YOUTUBE_MCP_BASE_DIR

# Entry point uses the command defined in pyproject.toml
ENTRYPOINT ["youtube-vision-transcriber"]
CMD ["--server"]
