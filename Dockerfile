# Use Ubuntu 20.04 as base image
FROM ubuntu:20.04

# Set environment variables to prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Update system and install basic dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg2 \
    software-properties-common

# Add MediaInfo repository for installing mediainfo dependencies
RUN add-apt-repository ppa:mediaarea/mediaarea && \
    apt-get update

# Install required dependencies
RUN apt-get install -y \
    mediainfo \
    libmediainfo0v5 \
    libzen0v5 \
    gnupg

# Download MEGAcmd package and install
RUN wget -O /tmp/megacmd.deb https://mega.nz/linux/MEGAsync/xUbuntu_20.04/amd64/megacmd-xUbuntu_20.04_amd64.deb && \
    apt-get install -y /tmp/megacmd.deb && \
    rm /tmp/megacmd.deb

# Clean up to reduce image size
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy bot files to /app
COPY . /app

# Install required Python packages from requirements.txt if it exists
RUN if [ -f requirements.txt ]; then pip3 install -r requirements.txt; fi

# Default command (replace 'bot.py' with your bot script if different)
CMD ["python3", "bot.py"]
