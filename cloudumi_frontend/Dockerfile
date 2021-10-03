# Build from the directory above this with:
# docker build . -f cloudumi_frontend/Dockerfile -t cloudumi_frontend
# docker run -p 80:80 cloudumi_frontend
FROM tiangolo/node-frontend as build-stage
WORKDIR /apps/cloudumi_frontend

COPY cloudumi_frontend/frontend/package*.json /apps/cloudumi_frontend/

RUN npm install --ignore-scripts

COPY cloudumi_frontend/frontend/ /apps/cloudumi_frontend/

RUN npm run build:prod

FROM nginx:1.15

#EXPOSE 80

COPY --from=build-stage /apps/cloudumi_frontend/build/ /usr/share/nginx/html

COPY --from=build-stage /nginx.conf /etc/nginx/conf.d/default.conf
