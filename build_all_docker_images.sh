set -x
docker build . --no-cache -f cloudumi_base_docker/Dockerfile -t cloudumi_base_docker &&
docker build . --no-cache -f cloudumi_common/Dockerfile -t cloudumi_common &&
docker build . --no-cache -f cloudumi_healthcheck/Dockerfile -t cloudumi_healthcheck &&
docker build . --no-cache -f cloudumi_frontend/Dockerfile -t cloudumi_frontend &&
docker build . --no-cache -f cloudumi_saml/Dockerfile -t cloudumi_saml &&
docker build . --no-cache -f cloudumi_api/Dockerfile -t cloudumi_api