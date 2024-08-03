# Use Python 3.11 slim-bullseye base image for a smaller footprint
FROM python:3.11-slim-bullseye as builder

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libportaudio2 \
    libavahi-compat-libdnssd-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Use multi-stage build to create a lean production image
FROM python:3.11-slim-bullseye

# Set working directory in the container
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only necessary files
COPY main.py .
COPY static ./static

# Create cache directory
RUN mkdir -p /app/static/cache && \
    # Create a non-root user
    useradd -m appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 5005

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Command to run the application with Uvicorn, trusting the proxy headers
CMD ["python", "main.py"]

