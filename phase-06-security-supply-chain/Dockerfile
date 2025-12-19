# Secure Dockerfile - Phase 6
# Demonstrates security best practices

# Use slim base image (smaller attack surface)
FROM python:3.11-slim

# Set environment variables for security and Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=phase6 \
    # Prevent pip from running as root
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Upgrade pip and system packages (security updates)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    # Minimal packages only if needed
    && rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip

# Install dependencies before copying source (better caching and security)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and group
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    # Ensure app directory is owned by appuser
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Copy application code (as late as possible for better caching)
COPY app.py .
RUN chown appuser:appuser app.py

# Switch to non-root user BEFORE running application
USER appuser

# Document the port (doesn't actually expose it)
EXPOSE 5000

# Healthcheck - lightweight liveness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"

# Run application as non-root user
CMD ["python", "app.py"]

