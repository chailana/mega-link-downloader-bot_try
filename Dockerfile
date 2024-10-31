# Use the official Ubuntu image as the base
FROM ubuntu:20.04

# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install prerequisites
RUN apt-get update && \
    apt-get install -y \
    software-properties-common \
    wget \
    python3 \
    python3-pip \
    apt-transport-https \
    ca-certificates \
    gnupg

# Install MediaInfo dependencies
RUN apt-get install -y \
    mediainfo \
    libmediainfo0v5 \
    libzen0v5 \
    gpg

# Download and install MEGAcmd directly from Mega's repository
RUN wget -O /tmp/megacmd.deb https://mega.nz/linux/MEGAsync/xUbuntu_20.04/amd64/megacmd-xUbuntu_20.04_amd64.deb && \
    apt-get install -y /tmp/megacmd.deb && \
    rm /tmp/megacmd.deb

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the application files
COPY . /app

# Install required Python packages from requirements.txt if it exists
RUN if [ -f requirements.txt ]; then pip3 install -r requirements.txt; fi

# Default command (replace 'bot.py' with your bot script if different)
CMD ["python3", "bot.py"]
