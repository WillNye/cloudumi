# Build from the directory above this with:
# docker build . -f cloudumi_base_docker/Dockerfile -t cloudumi_base_docker

FROM python:3.10
RUN mkdir -p /apps
RUN apt-get update
RUN apt-get install curl telnet iputils-ping sudo systemctl apt-transport-https -y

# logstash
# test with: /usr/share/logstash/bin/logstash -f /etc/logstash/conf.d/00-cloudumi-s3-es.conf
RUN bash -c 'wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch > /etc/apt/trusted.gpg.d/elasticsearch.gpg'
RUN bash -c 'gpg --dearmor /etc/apt/trusted.gpg.d/elasticsearch.gpg'
RUN bash -c 'echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee -a /etc/apt/sources.list.d/elastic-7.x.list'
RUN bash -c 'sudo apt-get update && sudo apt-get install logstash'
RUN systemctl enable logstash
RUN systemctl start logstash
ENV PKG_CONFIG_PATH=/usr/local/lib/x86_64-linux-gnu/pkgconfig:/usr/local/lib/pkgconfig:/usr/local/share/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig

# Metricsbeat (System metrics) for AMD64
# RUN curl -L -O https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-7.14.2-amd64.deb
# RUN dpkg -i metricbeat-7.14.2-amd64.deb
# RUN rm -rf metricbeat-7.14.2-amd64.deb

#COPY docker/base/root/ /

# TODO: Filebeat (elasticsearch to ingest system logs.)
#RUN curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.14.2-amd64.deb
#RUN dpkg -i filebeat-7.14.2-amd64.deb

# fluentbit
#RUN sudo wget -qO - http://packages.fluentbit.io/fluentbit.key ??? set as gpg key
#RUN sudo echo 'deb https://packages.fluentbit.io/ubuntu/focal focal main' >> /etc/apt/sources.list
#RUN sudo apt update
#RUN sudo apt install -y td-agent-bit
#RUN ln -s /lib/systemd/system/td-agent-bit.service /etc/systemd/system/td-agent-bit.service
#RUN systemctl start td-agent-bit

# Creates a non-root user with an explicit UID and adds permission to access the /apps folder
RUN addgroup --gid 1111 appgroup
RUN adduser -uid 1111 --gid 1111 --disabled-password --no-create-home --gecos "" appuser && chown -R appuser /apps
RUN mkdir -p /home/appuser/.aws/
RUN chown -R appuser /home/appuser