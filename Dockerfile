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
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
ENV BUILD_PATH=./frontend/build
ENV DISABLE_ESLINT_PLUGIN=true
ENV VIRTUAL_ENV=/app/env

RUN mkdir /app
WORKDIR /app
# Add PIP Requirements
ADD requirements.lock requirements.lock
ADD frontend/package.json frontend/package.json
ADD frontend/yarn.lock frontend/yarn.lock

# Install dependencies in as few layers as possible
RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata && apt-get install -y software-properties-common gcc && \
    add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && apt-get install -y python3.11 python3.11-distutils \
    python3-apt python3.11-dev python-is-python3 pkg-config awscli libpq-dev \
    git-all python3.11-venv curl telnet iputils-ping sudo vim systemctl apt-transport-https \
    build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev && \
    mkdir -p /app && \
    python -m ensurepip --upgrade && \
    apt-get clean && apt-get update && \
    # Install Node
    curl -sL https://deb.nodesource.com/setup_18.x | bash && \
    apt-get install -y nodejs && \
    # Install Fluent Bit
    curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | bash && \
    # Creates a non-root user with an explicit UID and adds permission to access the /app folder
    addgroup --gid 1111 appgroup && \
    adduser -uid 1111 --gid 1111 --disabled-password --no-create-home --gecos "" appuser && chown -R appuser /app && \
    mkdir -p /home/appuser/.aws/ && \
    chown -R appuser /home/appuser && \
    # Install Python requirements
    python -m venv $VIRTUAL_ENV && \
    . env/bin/activate && \
    python -m pip install -r requirements.lock && \
    # Install yarn and frontend dependencies
    npm install yarn -g && \
    yarn --cwd frontend --dev && \
    apt-get dist-upgrade -y

COPY configs/fluent-bit/fluent-bit.conf /etc/fluent-bit/fluent-bit.conf
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY frontend frontend
# We don't need node_modules after building, so we can remove it and save space
RUN yarn --cwd frontend build --base=$PUBLIC_URL && yarn --cwd frontend cache clean --all && rm -rf frontend/node_modules
COPY . /app
# Copy entrypoint.sh to use virtualenv and install API
RUN python3.11 -m pip install -e . && pip3 cache purge && apt-get -y autoremove

RUN $CONFIG_LOCATION || alembic upgrade head

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "api/__main__.py"]
