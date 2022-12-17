# For more information, please refer to https://aka.ms/vscode-docker-python
FROM ubuntu:latest
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETVARIANT

# Set environment variable PUBLIC_URL from build args, uses "/" as default
ARG PUBLIC_URL
ENV PUBLIC_URL=${PUBLIC_URL:-/}

RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata

RUN apt-get install -y software-properties-common gcc && \
    add-apt-repository -y ppa:deadsnakes/ppa

RUN apt-get update && apt-get install -y python3.10 python3-distutils \
    python3-pip python3-apt python3-dev python-is-python3 pkg-config \
    git-all

RUN mkdir -p /app
WORKDIR /app
RUN apt-get clean
RUN apt-get update
RUN apt-get install curl telnet iputils-ping sudo vim systemctl apt-transport-https -y
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash
RUN curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | bash
COPY configs/fluent-bit/fluent-bit.conf /etc/fluent-bit/fluent-bit.conf

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN addgroup --gid 1111 appgroup
RUN adduser -uid 1111 --gid 1111 --disabled-password --no-create-home --gecos "" appuser && chown -R appuser /app
RUN mkdir -p /home/appuser/.aws/
RUN chown -R appuser /home/appuser

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
ENV BUILD_PATH=./frontend/build
ENV DISABLE_ESLINT_PLUGIN=true

# Install system requirements
RUN apt-get install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y
# Install pip requirements
ADD requirements.lock .
RUN python -m pip install -r requirements.lock
RUN npm install yarn -g
ADD frontend/package.json frontend/package.json
ADD frontend/yarn.lock frontend/yarn.lock
RUN yarn --cwd frontend --dev
COPY frontend frontend
RUN yarn --cwd frontend build --base=$PUBLIC_URL
RUN echo $(pwd)
RUN cat frontend/dist/index.html
# RUN cat frontend/build/index.html | sed "s|PUBLIC_URL|${PUBLIC_URL}|g" > frontend/build/index.html
RUN yarn --cwd frontend cache clean --all
COPY . /app
# Install API
RUN python -m pip install -e .
RUN pip cache purge

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "api/__main__.py"]
