# Use an official Python runtime as a parent image
FROM python:3.12.6-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies for PDF processing and OCR using Chinese mirror source
RUN echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main" > /etc/apt/sources.list \
    && echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main" >> /etc/apt/sources.list \
    && echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-backports main" >> /etc/apt/sources.list \
    && echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        poppler-utils \
        libgomp1 \
        libjpeg62-turbo \
        libpng16-16 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements file
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies using Chinese mirror source
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy project
COPY backend/ /app/

# Create uploads directory for any temporary files
RUN mkdir -p uploads

# Expose port (using the configured port from app.conf)
EXPOSE 18080

# Health check
#HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#    CMD curl -f http://localhost:18080/docs || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "18080", "--reload"]