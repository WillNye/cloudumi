# Build from the directory above this with:
# docker build . -f cloudumi_router/Dockerfile -t cloudumi_router
# Run with: docker run -p 127.0.0.1:80:80/tcp cloudumi_router

FROM ubuntu
# Update the repository sources list
RUN apt-get update
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata
# Install and run apache
RUN apt-get install -y apache2 && apt-get clean

#ENTRYPOINT ["/usr/sbin/apache2", "-k", "start"]


#ENV APACHE_RUN_USER www-data
#ENV APACHE_RUN_GROUP www-data
#ENV APACHE_LOG_DIR /var/log/apache2

COPY cloudumi_router/root/etc/apache2/ /etc/apache2/

#EXPOSE 80
#EXPOSE 443
CMD ["apachectl", "-D", "FOREGROUND"]


# Build from the directory above this with:
# docker build . -f cloudumi_router/Dockerfile -t cloudumi_router
# Run with: docker run -p 127.0.0.1:8080:8080/tcp cloudumi_router
#FROM python
#RUN apt-get update
#RUN apt-get install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y
#RUN mkdir /apps
#COPY cloudumi_router/ /apps/cloudumi_router/
#WORKDIR /apps/cloudumi_router/
#RUN python -m pip install --upgrade pip
#RUN python -m pip install -r requirements.txt
#EXPOSE 8080
#CMD [ "uvicorn", "main:app", "--port=8080", "--host=0.0.0.0", "--reload"]