# Audiobookify Docker Image
# Convert EPUB and MOBI/AZW files to M4B audiobooks using Microsoft Edge TTS
#
# Build:
#   docker build -t audiobookify .
#
# Usage:
#   # Export EPUB to text
#   docker run -v $(pwd)/books:/books audiobookify /books/mybook.epub
#
#   # Convert text to audiobook
#   docker run -v $(pwd)/books:/books audiobookify /books/mybook.txt
#
#   # With cover image
#   docker run -v $(pwd)/books:/books audiobookify /books/mybook.txt --cover /books/cover.png
#
#   # Batch processing
#   docker run -v $(pwd)/books:/books audiobookify /books --batch
#
#   # Interactive shell
#   docker run -it -v $(pwd)/books:/books --entrypoint bash audiobookify

FROM python:3.11-slim

LABEL maintainer="audiobookify"
LABEL description="Convert EPUB and MOBI/AZW files to M4B audiobooks"
LABEL version="2.3.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"

# Copy application code
COPY epub2tts_edge/ ./epub2tts_edge/
COPY setup.py .
COPY README.md .

# Install the package
RUN pip install --no-cache-dir -e .

# Create volume mount point for books
VOLUME ["/books"]

# Set working directory for conversions
WORKDIR /books

# Default entrypoint is audiobookify
ENTRYPOINT ["audiobookify"]

# Default command shows help
CMD ["--help"]
