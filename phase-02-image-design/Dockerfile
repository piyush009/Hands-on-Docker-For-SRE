FROM python:3.11-slim

# Environment for predictable Python behavior and app env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=phase2

WORKDIR /app

# Upgrade pip first (separate layer for clarity)
RUN pip install --upgrade pip

# Install dependencies before copying source to improve cache hit rate
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code and set ownership
COPY app.py .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Document the port the app listens on
EXPOSE 5000

# Default command
CMD ["python", "app.py"]


