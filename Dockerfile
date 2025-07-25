# Use official Python image
FROM python:3.10-slim

# Install dependencies for playwright browsers
RUN apt-get update && apt-get install -y \
    curl \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxfixes3 \
    libxrender1 \
    libxcb1 \
    libdbus-1-3 \
    libxkbcommon0 \
    libglu1-mesa \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy your scraper files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers
RUN playwright install

# Set environment variable to avoid sandbox issues in Railway
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Command to run your scraper
CMD ["python", "scraper_bot.py"]