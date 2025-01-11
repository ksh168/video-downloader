# Use Python 3.11 slim image as base
FROM --platform=linux/amd64 python:3.11-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p downloads logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV PYTHONPATH=/app

# Expose port
EXPOSE 3001

# Run the application with Gunicorn using gevent worker
CMD ["gunicorn", "--worker-class", "gevent", "-w", "1", "--threads", "4", "--worker-connections", "50", "--timeout", "300", "--keep-alive", "5", "--bind", "0.0.0.0:3001", "app:app"]


# gunicorn --worker-class gevent -w 1 --bind 0.0.0.0:3001 app:app