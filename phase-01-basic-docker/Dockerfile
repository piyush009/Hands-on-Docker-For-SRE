FROM python:3.11-slim

# Avoid buffering logs and enable easier debugging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=container

WORKDIR /app

# Install system deps (kept minimal for now)
RUN pip install --upgrade pip

# Install Python deps first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Document the port the app listens on
EXPOSE 5000

# Default command
CMD ["python", "app.py"]


