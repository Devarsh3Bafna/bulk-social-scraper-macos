FROM python:3.11-slim

# Install system dependencies including Ruby and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ruby \
    ruby-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install webrick gem for Ruby
RUN gem install webrick

# Set working directory
WORKDIR /app

# Copy dependency specifications and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure working directories exist
RUN mkdir -p output downloads cache

# Set default port and Python buffering
ENV PORT=8501
ENV PYTHONUNBUFFERED=1

# Expose web server port
EXPOSE 8501

# Launch the live web server
CMD ["ruby", "server.rb"]
