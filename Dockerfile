# Multi-stage Dockerfile for Arakis API

# Stage 1: Builder - Install dependencies
FROM python:3.11-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first (for caching)
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime - Create production image
FROM python:3.11-slim AS runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 arakis && \
    mkdir -p /app && \
    chown -R arakis:arakis /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=arakis:arakis . .

# Switch to non-root user
USER arakis

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PATH="/home/arakis/.local/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check (uses PORT env var for Railway compatibility)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application
CMD ["sh", "-c", "uvicorn arakis.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
