# Build from the directory above this with:
# docker build . -f cloudumi_frontend/Dockerfile -t cloudumi_frontend
# docker run -p 80:80 cloudumi_frontend
FROM tiangolo/node-frontend as build-stage
#WORKDIR /apps/cloudumi_frontend
#
#COPY cloudumi_frontend/frontend/package*.json /apps/cloudumi_frontend/
#
#RUN npm install --ignore-scripts
#
#COPY cloudumi_frontend/ /apps/cloudumi_frontend/
#
#RUN npm run build:prod

FROM nginx:1.25

WORKDIR /apps/frontend
# Install Node, Yarn, and their dependencies
RUN apt-get clean
RUN apt-get update
RUN apt-get install curl gcc g++ make -y
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get update
RUN apt-get install nodejs build-essential -y
RUN npm install yarn -g

# Copy frontend on to container
COPY . /apps/frontend/
# Install node dependencies
RUN yarn

# Build static frontend
RUN yarn build


EXPOSE 8081

RUN cp -R /apps/frontend/build/* /usr/share/nginx/html

COPY --from=build-stage /nginx.conf /etc/nginx/conf.d/default.conf

RUN sed -i 's/listen 80;/listen 8081;/' /etc/nginx/conf.d/default.conf