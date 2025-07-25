FROM python:3.9-slim

# Install dependencies for Playwright browsers and tools
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libxshmfence1 \
    ca-certificates \
    fonts-liberation \
    libxkbcommon0 \
    libdbus-1-3 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers
RUN python -m playwright install

# Copy rest of app
COPY . .

# Run the script
CMD ["python", "scraper_bot.py"]