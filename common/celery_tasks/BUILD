load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package","py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")
load("@io_bazel_rules_docker//python:image.bzl", "py_layer")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")

INT_DEPS = [
    "//common/config:lib",
    "//common/exceptions:lib",
    "//common/lib",
    "//identity:lib",
    "//plugins/celery_tasks:lib",
    "//plugins/metrics:lib",
    "//util/log:lib",
]

EXT_DEPS = [
    requirement("aiohttp"),
    requirement("asgiref"),
    requirement("billiard"),
    requirement("celery"),
    requirement("checkov"),
    requirement("retrying"),
    requirement("sentry_sdk"),
    requirement("ujson"),
]

REQUIRES = [
    "aiohttp",
    "asgiref",
    "billiard",
    "celery",
    "checkov",
    "retrying",
    "sentry_sdk",
    "ujson",
]

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "celery_tasks.py",
        "run.py",
    ),
)

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.local",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
        "CONFIG_LOCATION": "$(RULEDIR)/configs/development_account:saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.s3",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
        "CONFIG_LOCATION": "s3://noq-tenant-configuration.node.dev1.259868150464.us-west-2/tenant_configurations/saas_development.yaml",
        "AWS_PROFILE": "noq_dev"
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_common_celery_tasks",
    python_tag = "py3",
    version = "0.0.1",
    deps = [":lib_pkg"],
    requires = REQUIRES,
    strip_path_prefixes = [
    ],
)

py_layer(
    name = "lib_layer",
    deps = [":lib"],
    filter = "@",
)

py_layer(
    name = "pkg_layer",
    deps = EXT_DEPS + INT_DEPS,
    filter = "@",
)

container_layer(
    name = "config_layer",
    files = [
        "//configs/development_account:configs",
    ],
    data_path = ".",
    directory = "/",
)

container_image(
    name = "base-celery-api",
    base = "//docker/base:base_docker",
    env = {
    },
    layers = [
        ":config_layer",
    ],
    ports = [],
    symlinks = {
        "/usr/bin/python": "/usr/local/bin/python",
    },
    docker_run_flags = "-v ~/.aws:/root/.aws",
)

py3_image(
    name = "container",
    base = ":base-celery-api",
    layers = [
        ":lib_layer",
        ":pkg_layer",
    ],
    srcs = [
        ":lib",
    ],
    deps = EXT_DEPS + INT_DEPS,
    main = "run.py",
    visibility = ["//visibility:public"],
)

container_push(
    name = "container-deploy-staging",
    format = "Docker",
    repository = "staging-registry-celery",
    image = "container",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "staging",
    visibility = ["//visibility:public"],
)

container_push(
    name = "container-deploy-prod",
    format = "Docker",
    repository = "prod-registry-celery",
    image = "container",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "production",
    visibility = ["//visibility:public"],
)