# Build from the directory above this with:
# docker build . -f cloudumi_common/Dockerfile -t cloudumi_common

FROM cloudumi_base_docker
RUN apt-get update
RUN apt-get install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y
COPY cloudumi_common/ /apps/cloudumi_common/
COPY cloudumi_config/ /apps/cloudumi_config/
WORKDIR /apps/cloudumi_common/
RUN python -m pip install --upgrade pip
RUN pip install /apps/cloudumi_common/
RUN pip install /apps/cloudumi_common/cloudumi_plugins
RUN python -m pip install -r requirements.txt
RUN python -m pip install -e .
ENV CONFIG_LOCATION=/apps/cloudumi_config/configs/development_account/saas_development.yaml
# TODO: figure out how to securely get AWS credentials readable by non-root user so we can have everything run as appuser
#USER appuser