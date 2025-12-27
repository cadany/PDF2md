# Use an official Python runtime as a parent image
FROM python:3.9.6-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies for PaddleOCR
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        pkg-config \
        gcc \
        g++ \
        poppler-utils \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY backend/ /app/

# Create uploads directory for any temporary files
RUN mkdir -p uploads

# Expose port (if running as a service)
EXPOSE 5000

# Run the application
CMD ["python", "run.py"]