FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for sqlite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for sqlite
RUN mkdir -p /app/data

# Copy application code
COPY app/ app/

# Environment variables
ENV FLASK_APP=app:create_app()
ENV FLASK_ENV=production

# Expose port 80
EXPOSE 80

# Use Gunicorn as the WSGI server, bind to port 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "2", "--threads", "4", "--timeout", "60", "app:create_app()"]
