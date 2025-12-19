FROM python:3.11-slim

# Environment for predictable Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=phase3

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies before copying source (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY app.py .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Document the port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]

