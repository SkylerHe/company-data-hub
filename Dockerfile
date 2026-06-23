# Company Data Hub - Equity Research Data Collection System
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py .
COPY *.sh .
COPY *.yaml .
COPY *.json .
COPY *.md .

# Make scripts executable
RUN chmod +x *.sh *.py

# Create data directory for SQLite database
RUN mkdir -p /data

# Set environment variable for database location
ENV DB_PATH=/data/finance.db

# Expose dashboard port
EXPOSE 8000

# Default command: run dashboard
CMD ["python", "dashboard.py"]
