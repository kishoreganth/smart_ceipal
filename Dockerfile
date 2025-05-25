# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Set working directory
WORKDIR /smart_ceipal

# Install system dependencies including Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    jq \
    # Chrome dependencies
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and .env file
COPY . .

# Create necessary directories
RUN mkdir -p drivers resources

# Download and install ChromeDriver using the new Chrome for Testing API
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && echo "Chrome version: $CHROME_VERSION" \
    && CHROMEDRIVER_URL="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" \
    && CHROMEDRIVER_VERSION=$(curl -s $CHROMEDRIVER_URL | jq -r ".versions[] | select(.version==\"$CHROME_VERSION\") | .downloads.chromedriver[] | select(.platform==\"linux64\") | .url" | head -1) \
    && if [ -z "$CHROMEDRIVER_VERSION" ]; then \
        echo "Exact version not found, trying latest stable..." \
        && CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json" | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url'); \
    fi \
    && echo "ChromeDriver URL: $CHROMEDRIVER_VERSION" \
    && wget -O /tmp/chromedriver.zip "$CHROMEDRIVER_VERSION" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && find /tmp -name "chromedriver" -type f -exec mv {} ./drivers/chromedriver \; \
    && chmod +x ./drivers/chromedriver \
    && rm -rf /tmp/chromedriver* \
    && ./drivers/chromedriver --version

# Expose port 8000
EXPOSE 8000

# Start Xvfb and run the application with proper cleanup
CMD ["sh", "-c", "rm -f /tmp/.X99-lock && Xvfb :99 -screen 0 1024x768x16 -ac +extension GLX +render -noreset & sleep 2 && uvicorn api:app --host 0.0.0.0 --port 8000"] 