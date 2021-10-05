# Build from the directory above this with:
# docker build . -f cloudumi_base_docker/Dockerfile -t cloudumi_base_docker

FROM python
RUN mkdir -p /apps
RUN apt-get update
RUN apt-get install telnet iputils-ping sudo vim -y

COPY cloudumi_base_docker/root/ /

# Creates a non-root user with an explicit UID and adds permission to access the /apps folder
RUN addgroup --gid 1111 appgroup
RUN adduser -uid 1111 --gid 1111 --disabled-password --no-create-home --gecos "" appuser && chown -R appuser /apps
RUN mkdir -p /home/appuser/.aws/
RUN chown -R appuser /home/appuser