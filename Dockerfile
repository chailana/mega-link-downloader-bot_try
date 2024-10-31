# Solely coded by xmysteriousx
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

# Set up the working directory in the container
RUN mkdir -p /app && chmod 777 /app
WORKDIR /app

# Install necessary packages
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
    automake && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Installing MEGAcmd
RUN wget -O /tmp/megacmd.deb https://mega.nz/linux/MEGAsync/xUbuntu_20.04/amd64/megacmd-xUbuntu_20.04_amd64.deb && \
    apt-get install -y /tmp/megacmd.deb && \
    rm /tmp/megacmd.deb

# Installing megatools from source
RUN git clone https://github.com/XMYSTERlOUSX/megatools /tmp/megatools && \
    cd /tmp/megatools && \
    meson b && ninja -C b && ninja -C b install && \
    rm -rf /tmp/megatools

# Copying the content of the local src directory to the working directory
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Start the application
CMD gunicorn app:app & python3 bot.py
