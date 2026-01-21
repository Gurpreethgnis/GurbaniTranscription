# Use NVIDIA CUDA base image for GPU support
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.11 and set up symlinks
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && (rm -f /usr/bin/python3 /usr/bin/python || true) \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    python3-pip \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install PyTorch nightly with CUDA 12.8+ support for RTX 50 series (sm_120/Blackwell)
# Must use cu128 for sm_120 support
RUN pip install --no-cache-dir --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# Install CTranslate2 with CUDA support for faster-whisper
# This is the backend that faster-whisper uses - separate from PyTorch
RUN pip install --no-cache-dir ctranslate2

# Install other Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p uploads outputs/transcriptions outputs/json outputs/formatted logs data \
    && chmod -R 755 uploads outputs logs data

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Default admin credentials (override in production!)
ENV ADMIN_EMAIL=admin@shabadguru.local
ENV ADMIN_PASSWORD=changeme123

# Database location (use persistent volume in production)
ENV DATABASE_URL=sqlite:////app/data/shabad_guru.db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/status || exit 1

# Run the application
CMD ["python", "app.py"]
