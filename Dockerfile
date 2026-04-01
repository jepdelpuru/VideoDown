# Use official Python image (explicitly Bookworm for stability)
FROM python:3.11-slim-bookworm

# Install system dependencies (FFmpeg is essential for yt-dlp)
# Use --no-install-recommends to avoid unnecessary packages like systemd
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (required by yt-dlp for YouTube JS extraction)
RUN curl -fsSL https://github.com/denoland/deno/releases/download/v2.7.9/deno-x86_64-unknown-linux-gnu.zip -o /tmp/deno.zip && \
    unzip /tmp/deno.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/deno && \
    rm /tmp/deno.zip

# Set working directory
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/downloads

# Expose the application port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
