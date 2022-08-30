load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package","py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")
load("@io_bazel_rules_docker//python:image.bzl", "py_layer")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")

INT_DEPS = [
    "//common/config:lib",
    "//common/exceptions:lib",
    "//common/aws:lib",
    "//common/lib",
    "//common/lib/aws/access_undenied:lib",
    "//common/user_request:lib",
    "//identity:lib",
    "//plugins/auth:lib",
    "//plugins/aws:lib",
    "//plugins/celery_tasks:lib",
    "//plugins/config:lib",
    "//plugins/group_mapping:lib",
    "//plugins/metrics:lib",
    "//plugins/policies:lib",
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
        "auth.py",
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
    name = "bin",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_cluster_dev",
        "AWS_REGION": "us-west-2",
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_common_celery_tasks",
    python_tag = "py3",
    version = "0.0.1",
    deps = [":lib"],
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

container_image(
    name = "base-celery-api",
    base = "//docker/base:base_docker",
    env = {
        "DEBUG": "1",
    },
    layers = [
        "//deploy/layers:config",
        "//deploy/layers:web_site",
        "//deploy/layers:celery_tasks.sshd_config",
        "//deploy/layers:weep",
    ],
    ports = ["2223"],
    symlinks = {
        "/usr/bin/python": "/usr/local/bin/python",
    },
    docker_run_flags = "-v ~/.aws:/root/.aws",
)

container_image(
    name = "base-celery-dev-local",
    base = "//docker/base:base_docker",
    env = {
        "TZ": "America/Los_Angeles",
        "CONFIG_LOCATION": "/configs/development_account/saas_development.yaml",
        "NOQ_CONTAINER": "1",
        "AWS_PROFILE": "noq_dev",
        "DEBUG": "1",
    },
    layers = [
        "//deploy/layers:config",
        "//deploy/layers:web_site",
        "//deploy/layers:celery_tasks.sshd_config",
        "//deploy/layers:weep",
    ],
    ports = ["2223"],
    symlinks = {
        "/usr/bin/python": "/usr/local/bin/python",
    },
    docker_run_flags = "-v ~/.aws:/root/.aws",
)

py3_image(
    name = "container",
    base = ":base-celery-api",
    srcs = [
        ":lib",
    ],
    layers = [
        ":lib_layer",
        ":pkg_layer",
    ],
    deps = EXT_DEPS + INT_DEPS,
    main = "run.py",
    visibility = ["//visibility:public"],
)

py3_image(
    name = "container-dev-local",
    base = ":base-celery-dev-local",
    srcs = [
        ":lib",
    ],
    layers = [
        ":pkg_layer",
        ":lib_layer",
    ],
    deps = EXT_DEPS + INT_DEPS,
    main = "run.py",
    visibility = ["//visibility:public"],
)