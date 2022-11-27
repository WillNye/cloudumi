# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETVARIANT
RUN mkdir -p /app
WORKDIR /app
RUN apt clean
RUN apt update

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
RUN yarn --cwd frontend build
RUN yarn --cwd frontend cache clean --all
COPY . /app
# Install API
RUN python -m pip install -e .
RUN pip cache purge

# Install SPA frontend


# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "api/__main__.py"]
