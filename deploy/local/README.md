# Local Deploy
This service deploys a local cluster and populates it with a sample localhost tenant. In order to update the sample localhost tenant, see the `populate_services.py` file.

## Deploy services
* `bazel run //deploy/local:deps-only`
* `bazel run //deploy/local:populate_services`

## Kill services
* `bazel run //deploy/local:kill-deps-only`