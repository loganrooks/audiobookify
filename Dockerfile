# Audiobookify Docker Image
# Convert EPUB and MOBI/AZW files to M4B audiobooks using Microsoft Edge TTS
#
# Build:
#   docker build -t audiobookify .
#
# Usage:
#   # Export EPUB to text
#   docker run --rm -v "$(pwd)/books:/books" audiobookify /books/mybook.epub
#
#   # Convert text to audiobook
#   docker run --rm -v "$(pwd)/books:/books" audiobookify /books/mybook.txt
#
#   # With cover image
#   docker run --rm -v "$(pwd)/books:/books" audiobookify /books/mybook.txt --cover /books/cover.png
#
#   # Batch processing
#   docker run --rm -v "$(pwd)/books:/books" audiobookify /books --batch
#
#   # Interactive shell
#   docker run --rm -it -v "$(pwd)/books:/books" --entrypoint bash audiobookify

FROM python:3.11-slim

# Version is injected at build time from pyproject.toml (see release workflow)
# rather than hardcoded, so it cannot drift out of date.
ARG VERSION=dev

LABEL org.opencontainers.image.title="audiobookify" \
      org.opencontainers.image.description="Convert EPUB and MOBI/AZW files to M4B audiobooks" \
      org.opencontainers.image.source="https://github.com/loganrooks/audiobookify" \
      org.opencontainers.image.licenses="GPL-3.0" \
      org.opencontainers.image.version="${VERSION}"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first for better layer caching.
# pyproject.toml is REQUIRED: without it the build falls back to the minimal
# setup.py, which declares no [project.scripts], and the `audiobookify`
# entrypoint below would not exist.
COPY pyproject.toml setup.py README.md requirements.txt ./

# Install Python dependencies (cached unless the manifests change)
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data into a shared location readable by the runtime user
ENV NLTK_DATA=/usr/local/share/nltk_data
RUN python -c "import nltk; nltk.download('punkt', download_dir='$NLTK_DATA', quiet=True); nltk.download('punkt_tab', download_dir='$NLTK_DATA', quiet=True)"

# Copy application code and install the package itself
COPY epub2tts_edge/ ./epub2tts_edge/
RUN pip install --no-cache-dir .

# Run as a non-root user. Books are bind-mounted, so make the mount point
# owned by that user for write access to generated output.
RUN useradd --create-home --uid 1000 audiobookify \
    && mkdir -p /books \
    && chown audiobookify:audiobookify /books
USER audiobookify

VOLUME ["/books"]
WORKDIR /books

ENTRYPOINT ["audiobookify"]
CMD ["--help"]
