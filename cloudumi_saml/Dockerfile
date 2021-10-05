# Build from the directory above this with:
# docker build . -f cloudumi_saml/Dockerfile -t cloudumi_saml
# Run with: docker run -p 127.0.0.1:8091:8091/tcp cloudumi_saml
# Pass credentials with:
# docker run -p 127.0.0.1:8091:8091/tcp -v "/home/ccastrapel/.aws:/root/.aws:cached" cloudumi_saml

FROM cloudumi_common
COPY cloudumi_saml/ /apps/cloudumi_saml/
RUN pip install /apps/cloudumi_saml
EXPOSE 8091
# Give Localstack enough time to start up by sleeping first. We don't need this in production.
CMD python /apps/cloudumi_saml/cloudumi_saml/__main__.py