# Build from the directory above this with:
# docker build . -f cloudumi_saml/Dockerfile -t cloudumi_saml
# Run with: docker run -p 127.0.0.1:80:80/tcp cloudumi_saml

FROM python
RUN apt-get update
RUN apt-get install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y
RUN mkdir /apps
COPY cloudumi_saml/ /apps/cloudumi_saml/
COPY cloudumi_common/ /apps/cloudumi_common/
WORKDIR /apps/cloudumi_saml/
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
RUN python -m pip install -e .
EXPOSE 8080
CMD [ "python", "main:app", "--port=8080", "--host=0.0.0.0", "--reload"]