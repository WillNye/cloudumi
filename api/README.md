# API

## Quick Start

- Activate your local virtualenv first `. env/bin/activate` (Note: We haven't had success working with pyenv)
- Run a local test of the API service using one of the py_binary targets.

## OpenAPI Spec

We use Postman to design and test our API. We use the OpenAPI spec (swagger) to convert the spec into python models. In order to connect the Postman output with Swagger, we use https://joolfe.github.io/postman-to-openapi/.

Once you have the Postman API in a satisfactory state, export the collection to file (assuming `api/CloudUmi v2 API.postman_collection.json`)

- Install: `sudo npm i postman-to-openapi -g`
- Operate: `p2o ./CloudUmi\ v2\ API.postman_collection.json -f ../common/util/swagger.yaml`
