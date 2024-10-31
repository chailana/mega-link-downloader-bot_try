# Start with an Ubuntu 20.04 base image
FROM ubuntu:20.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

# Set up the working directory in the container
RUN mkdir -p /app && chmod 777 /app
WORKDIR /app

# Update the package list and install dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    git \
    python3 \
    python3-pip \
    make \
    wget \
    ffmpeg \
    meson \
    libglib2.0-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    asciidoc \
    docbook-xml \
    autoconf \
    libtool \
    automake \
    snapd && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Enable snapd, install and set up MEGAcmd
RUN systemctl enable snapd && \
    snap install core && \
    snap install megacmd --classic

# Copy the content of the local src directory to the working directory
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Start the application
CMD gunicorn app:app & python3 bot.py
