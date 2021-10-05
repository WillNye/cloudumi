# Build from the directory above this with:
# docker build . -f cloudumi_api/Dockerfile -t cloudumi_api
# Run with: docker run -p 127.0.0.1:8092:8092/tcp cloudumi_api
# Pass credentials with:
# docker run -p 127.0.0.1:8091:8092/tcp -v "/home/ccastrapel/.aws:/root/.aws:cached"    cloudumi_api

FROM cloudumi_common

# TODO: Below settings are only for debugging in Dev
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

COPY cloudumi_api/ /apps/cloudumi_api/
RUN pip install /apps/cloudumi_api
EXPOSE 8092

# Give Localstack enough time to start up by sleeping first. We don't need this in production.
CMD python /apps/cloudumi_api/cloudumi_api/__main__.py