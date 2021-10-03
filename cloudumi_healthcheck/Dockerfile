# Build from the directory above this with:
# docker build . -f cloudumi_healthcheck/Dockerfile -t cloudumi_healthcheck
# Run with: docker run -p 127.0.0.1:8090:8090/tcp cloudumi_healthcheck
FROM python

RUN mkdir /apps
COPY cloudumi_healthcheck/ /apps/cloudumi_healthcheck/
WORKDIR /apps/cloudumi_healthcheck/
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
EXPOSE 8090
CMD [ "uvicorn", "main:app", "--port=8090", "--host=0.0.0.0"]