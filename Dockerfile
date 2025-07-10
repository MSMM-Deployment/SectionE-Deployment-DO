# =================================================================
# Dockerfile for Section E Resume Parser & Database System
# Digital Ocean Container Deployment
# =================================================================

# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set metadata
LABEL maintainer="rmehta@msmmeng.com"
LABEL description="Section E Resume Parser & Database System"
LABEL version="2.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=2
ENV PORT=8000

# Create app user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    antiword \
    poppler-utils \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/ParsedFiles data/OutputFiles temp_processing && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE $PORT

# Start command
CMD ["python", "start_server.py"]

# =================================================================
# Build and Run Instructions:
# =================================================================
# 
# Build the image:
#   docker build -t sectionE-parser:latest .
# 
# Run container with environment variables:
#   docker run -d \
#     --name sectionE-parser \
#     -p 8000:8000 \
#     -e SUPABASE_URL="https://your-project.supabase.co" \
#     -e SUPABASE_KEY="your_supabase_key" \
#     -e OPENAI_API_KEY="sk-your-openai-key" \
#     -e NODE_ENV="production" \
#     -e PYTHON_ENV="production" \
#     sectionE-parser:latest
# 
# Run with environment file:
#   docker run -d \
#     --name sectionE-parser \
#     -p 8000:8000 \
#     --env-file .env \
#     sectionE-parser:latest
# 
# View logs:
#   docker logs -f sectionE-parser
# 
# Execute shell in container:
#   docker exec -it sectionE-parser /bin/bash
# 
# Stop container:
#   docker stop sectionE-parser
# 
# Remove container:
#   docker rm sectionE-parser
# 
# For Digital Ocean Container Registry:
#   docker tag sectionE-parser:latest registry.digitalocean.com/your-registry/sectionE-parser:latest
#   docker push registry.digitalocean.com/your-registry/sectionE-parser:latest
# ================================================================= 