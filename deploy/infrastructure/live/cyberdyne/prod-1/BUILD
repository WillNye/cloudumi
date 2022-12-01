load("@io_bazel_rules_docker//container:container.bzl", "container_push")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

EXT_DEPS = [
    requirement("boto3"),
    requirement("pyyaml"),
    requirement("semver"),
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
    repository = "cyberdyne-prod-registry-api",
    image = "//api:container",
    registry = "775726381634.dkr.ecr.us-west-2.amazonaws.com",
    tag = "{VERSION}",
    visibility = ["//visibility:public"],
)

container_push(
    name = "celery-container-deploy-prod",
    format = "Docker",
    repository = "cyberdyne-prod-registry-celery",
    image = "//common/celery_tasks:container",
    registry = "775726381634.dkr.ecr.us-west-2.amazonaws.com",
    tag = "{VERSION}",
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

py_binary(
    name = "ecs_undeployer",
    srcs_version = "PY3",
    srcs = [
        "ecs_undeployer.py",
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
    cmd = "ecs-cli compose -f deploy/infrastructure/live/cyberdyne/prod-1/compose.yaml \
           -p cyberdyne-noq-dev-cyberdyne-prod-1 service rm \
           \
           ecs-cli down --cluster-config cyberdyne-noq-dev-cyberdyne-prod-1; >$@",
    tags = ["manual"],
)