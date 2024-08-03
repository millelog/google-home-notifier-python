# Use Python 3.11 base image
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libportaudio2 \
    libavahi-compat-libdnssd-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create cache directory
RUN mkdir -p /app/static/cache

# Expose the port the app runs on
EXPOSE 5001

# Command to run the application
CMD ["python", "main.py"]