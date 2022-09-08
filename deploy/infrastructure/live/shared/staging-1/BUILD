load("@io_bazel_rules_docker//container:container.bzl", "container_push")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

EXT_DEPS = [
    requirement("boto3"),
    requirement("pyyaml"),
    requirement("semver"),
]
filegroup(
    name = "staging-1-files",
    srcs = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

container_push(
    name = "api-container-deploy-staging",
    format = "Docker",
    repository = "shared-staging-registry-api",
    image = "//api:container",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "{VERSION}",
    visibility = ["//visibility:public"],
)

container_push(
    name = "celery-container-deploy-staging",
    format = "Docker",
    repository = "shared-staging-registry-celery",
    image = "//common/celery_tasks:container",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "{VERSION}",
    visibility = ["//visibility:public"],
)

py_binary(
    name = "ecs_deployer",
    srcs_version = "PY3",
    data = [
        "staging-1-files",
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

py_binary(
    name = "upload_to_cdn",
    srcs_version = "PY3",
    srcs = [
        "upload_cdn.py",
    ],
    deps = EXT_DEPS,
    visibility = ["//visibility:public"],
)

genrule(
    name = "destroy",
    srcs = [
        ":staging-1-files",
    ],
    executable = True,
    outs = ["run_destroy_staging"],
    message = "Destroying CloudUmi in staging...",
    cmd = "ecs-cli compose -f deploy/infrastructure/live/shared/staging-1/compose.yaml \
           -p staging-noq-dev-shared-staging-1 service rm \
           \
           ecs-cli down --cluster-config staging-noq-dev-shared-staging-1; >$@",
    tags = ["manual"],
)