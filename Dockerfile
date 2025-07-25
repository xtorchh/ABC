# Use official Playwright Python image (latest stable)
FROM mcr.microsoft.com/playwright/python:v1.48.0-focal

# Set working directory inside container
WORKDIR /app

# Copy all your project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run your scraper script when container starts
CMD ["python", "scraper_bot.py"]