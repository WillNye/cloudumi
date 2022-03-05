load("@io_bazel_rules_docker//container:container.bzl", "container_push")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

EXT_DEPS = [
    requirement("boto3"),
]
filegroup(
    name = "prod-1-files",
    srcs = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

container_push(
    name = "api-container-deploy-prod",
    format = "Docker",
    repository = "shared-prod-registry-api",
    image = "//api:container",
    registry = "940552945933.dkr.ecr.us-west-2.amazonaws.com",
    tag = "prod",
    visibility = ["//visibility:public"],
)

container_push(
    name = "celery-container-deploy-prod",
    format = "Docker",
    repository = "shared-prod-registry-celery",
    image = "//common/celery_tasks:container",
    registry = "940552945933.dkr.ecr.us-west-2.amazonaws.com",
    tag = "prod",
    visibility = ["//visibility:public"],
)

py_binary(
    name = "ecs_deployer",
    srcs_version = "PY3",
    data = [
    "prod-1-files",
    ],
    srcs = [
        "ecs_deployer.py",
    ],
    deps = EXT_DEPS,
    visibility = ["//visibility:public"],
)

genrule(
    name = "destroy",
    srcs = [
        ":prod-1-files",
    ],
    executable = True,
    outs = ["run_destroy_prod"],
    message = "Destroying CloudUmi in prod...",
    cmd = "ecs-cli compose -f deploy/infrastructure/live/shared/prod-1/compose.yaml \
           -p noq-dev-shared-prod-1 service rm \
           \
           ecs-cli down --cluster-config noq-dev-shared-prod-1; >$@",
    tags = ["manual"],
)