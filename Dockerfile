# ================================
# Base Image
# ================================
FROM python:3.11-slim

# ================================
# Environment
# ================================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Aden
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ================================
# System Dependencies
# ================================
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libxkbcommon0 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    tzdata \
    procps \
    && rm -rf /var/lib/apt/lists/*

# ================================
# Timezone
# ================================
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ================================
# Working Directory
# ================================
WORKDIR /app

# ================================
# Python Dependencies (FIXED)
# ================================
RUN pip install --no-cache-dir --upgrade pip

# 1. Copy requirements first
COPY requirements.txt .

# 2. Install ALL dependencies from the file (Solves ddddocr missing issue)
RUN pip install --no-cache-dir -r requirements.txt

# ================================
# Install Playwright
# ================================
RUN playwright install chromium --with-deps

# ================================
# Copy Application
# ================================
COPY . /app

# Ensure evidence directory exists
RUN mkdir -p /app/evidence

# ================================
# Healthcheck
# ================================
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# ================================
# Run
# ================================
CMD ["python", "-m", "src.main"]