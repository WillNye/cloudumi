# API

## Quick Start

- Activate your local virtualenv first `. env/bin/activate` (Note: We haven't had success working with pyenv)
- Run a local test of the API service using one of the py_binary targets.
  - To run local-dev: `bazelisk run //api:bin`
  - To run S3-dev: `bazelisk run //api:bin.s3` -- note that the only difference here is that the config files are pulled from S3
- Build the API project library: `bazelisk build //api:lib`
- Test the API project library: `bazelisk test //api` -- coming SOON
- Run the API project local dev container: `bazelisk run //api:container-dev-local`
- Deploy the API project container to staging: `bazelisk run //api:container-deploy-staging`
- Deploy the API project container to production: `bazelisk run //api:container-deploy-prod`
- For development, you can use `ibazel` as well and run the `//api:bin` target using ibazel: `ibazel run //api:bin`; anytime a change is made to the `frontend` or the `api` the system will automatically rebuild and restart.

## OpenAPI Spec

We use Postman to design and test our API. We use the OpenAPI spec (swagger) to convert the spec into python models. In order to connect the Postman output with Swagger, we use https://joolfe.github.io/postman-to-openapi/.

Once you have the Postman API in a satisfactory state, export the collection to file (assuming `api/CloudUmi v2 API.postman_collection.json`)

- Install: `sudo npm i postman-to-openapi -g`
- Operate: `p2o ./CloudUmi\ v2\ API.postman_collection.json -f ../common/util/swagger.yaml`
