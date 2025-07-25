# Use official Playwright Python image with all dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.35.1-focal

# Set working directory inside container
WORKDIR /app

# Copy all your project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run your scraper script when container starts
CMD ["python", "scraper_bot.py"]