# TODO: @ccastrapel: I don't think we need this anymore
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
# logstash
# test with: /usr/share/logstash/bin/logstash -f /etc/logstash/conf.d/00-cloudumi-s3-es.conf
RUN bash -c 'wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -'
RUN bash -c 'echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee -a /etc/apt/sources.list.d/elastic-7.x.list'
RUN bash -c 'sudo apt-get update && sudo apt-get install logstash'
RUN systemctl enable logstash
RUN systemctl start logstash

# Metricsbeat (System metrics)
# RUN curl -L -O https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-7.14.2-amd64.deb
# RUN dpkg -i metricbeat-7.14.2-amd64.deb
# RUN rm -rf metricbeat-7.14.2-amd64.deb

# TODO: Filebeat (elasticsearch to ingest system logs.)
#RUN curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.14.2-amd64.deb
#RUN dpkg -i filebeat-7.14.2-amd64.deb

# fluentbit
#RUN sudo wget -qO - http://packages.fluentbit.io/fluentbit.key | sudo apt-key add -
#RUN sudo echo 'deb https://packages.fluentbit.io/ubuntu/focal focal main' >> /etc/apt/sources.list
#RUN sudo apt update
#RUN sudo apt install -y td-agent-bit
#RUN ln -s /lib/systemd/system/td-agent-bit.service /etc/systemd/system/td-agent-bit.service
#RUN systemctl start td-agent-bit

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
COPY . /app
RUN yarn --cwd frontend --dev
RUN python -m pip install -e .

# Install SPA frontend
RUN yarn --cwd frontend build

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "api/__main__.py"]
