# For more information, please refer to https://aka.ms/vscode-docker-python
FROM ubuntu:latest
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETVARIANT
ARG IAMBIC_REPO_USER
ARG IAMBIC_REPO_TOKEN
ENV IAMBIC_REPO_USER=$IAMBIC_REPO_USER
ENV IAMBIC_REPO_TOKEN=$IAMBIC_REPO_TOKEN

# Set environment variable PUBLIC_URL from build args, uses "/" as default
ARG PUBLIC_URL
ENV PUBLIC_URL=${PUBLIC_URL:-/}
ARG PUBLIC_URL_V2
ENV PUBLIC_URL_V2=${PUBLIC_URL_V2:-/}
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
ENV BUILD_PATH=./frontend/build
ENV DISABLE_ESLINT_PLUGIN=true
ENV VIRTUAL_ENV=/app/env
ENV NODE_OPTIONS=--openssl-legacy-provider

RUN mkdir /app
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata software-properties-common gcc && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y gdb ncat openssh-server python3.11 python3.11-distutils python3-apt python3.11-dev python-is-python3 pkg-config awscli libpq-dev git-all python3.11-venv curl telnet iputils-ping sudo systemctl apt-transport-https libgtk2.0-0 libgtk-3-0 libgbm-dev libnotify-dev libgconf-2-4 libnss3 libxss1 libasound2 libxtst6 xauth xvfb build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev unzip

# Configure sshd
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Install pip, node and fluent-bit
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash && \
    apt-get install -y nodejs && \
    curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | bash

# Add user
RUN addgroup --gid 1111 appgroup && \
    adduser -uid 1111 --gid 1111 --disabled-password --no-create-home --gecos "" appuser && \
    chown -R appuser /app && \
    mkdir -p /home/appuser/.aws/ && \
    chown -R appuser /home/appuser

# Install project dependencies
COPY requirements.lock requirements.lock
RUN  python3.11 -m venv $VIRTUAL_ENV && \
    . env/bin/activate && \
    python3.11 -m pip install -r requirements.lock

# Install frontend
COPY frontend/package.json frontend/yarn.lock ./frontend/
COPY ui/package.json ui/yarn.lock ./ui/
RUN npm install yarn -g && \
    yarn --cwd frontend --dev && \
    yarn --cwd ui

# Clean Up
RUN apt-get clean && \
    apt-get -y autoremove && \
    apt-get dist-upgrade -y

# Install AWS CLI
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        export ARCH="x86_64" ; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        export ARCH="aarch64" ; \
    else \
        echo "Unsupported architecture" && exit 1 ; \
    fi && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-$ARCH.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    sudo ./aws/install && \
    rm -rf awscliv2.zip aws

COPY configs/fluent-bit/fluent-bit.conf /etc/fluent-bit/fluent-bit.conf
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

COPY frontend frontend
COPY ui ui

# We don't need node_modules after building, so we can remove it and save space
RUN yarn --cwd frontend build --base=$PUBLIC_URL && \
    yarn --cwd frontend cache clean --all && \
    rm -rf frontend/node_modules && \
    yarn --cwd ui build --base=$PUBLIC_URL_V2 && \
    yarn --cwd ui cache clean --all && \
    rm -rf ui/node_modules

WORKDIR /app
COPY . /app
# Copy entrypoint.sh to use virtualenv and install API
RUN python3.11 -m pip install -e . && \
    pip3 cache purge && \
    apt-get -y autoremove
RUN rm -rf /root/.cache/

RUN $CONFIG_LOCATION || alembic upgrade head

# This is just to print out the installed packages so we can quickly compare version differences if
# something breaks.

RUN dpkg --list

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python3.11", "api/__main__.py"]