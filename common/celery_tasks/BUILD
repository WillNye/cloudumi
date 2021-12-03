load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package","py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")
#load("@rules_pkg//:pkg.bzl", "pkg_tar")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "celery_tasks.py",
        "run.py",
    ),
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = [
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins:lib",
        "//plugins/auth:lib",
        "//plugins/celery_tasks:lib",
        "//plugins/config:lib",
        "//plugins/metrics:lib",
        "//util/log:lib",
        requirement("celery"),
        requirement("ujson"),
    ],
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
        #"CONFIG_LOCATION": "$(RULEDIR)/configs/development_account:saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins:lib",
        "//plugins/auth:lib",
        "//plugins/celery_tasks:lib",
        "//plugins/config:lib",
        "//plugins/metrics:lib",
        "//util/log:lib",
        requirement("celery"),
        requirement("ujson"),
    ],
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
    deps = [
        requirement("celery"),
        requirement("ujson"),
    ],
    visibility = ["//visibility:public"],
)

py_package(
    name = "lib_pkg",
    deps = [
        ":lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins:lib",
        "//plugins/auth:lib",
        "//plugins/celery_tasks:lib",
        "//plugins/config:lib",
        "//plugins/metrics:lib",
        "//util/log:lib",
        requirement("celery"),
        requirement("ujson"),
    ],
    packages = [
        "common/celery_tasks",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_common_celery_tasks",
    python_tag = "py3",
    version = "0.0.1",
    # entry_points = {
    #     "console_scripts": [""],
    # },
    deps = [":lib_pkg"],
    requires = ["celery", "ujson"],
    strip_path_prefixes = [
    ],
)

container_layer(
    name = "lib_layer",
    files = [
        ":lib",
    ],
    data_path = ".",
    directory = "/",
)

container_image(
    name = "container",
    base = "//docker/base:base_docker",
    files = [
        "//configs/development_account:configs",
    ],
    layers = [
        ":lib_layer",
    ],
    env = {
        "TZ": "America/Los_Angeles",
        "PYTHONPATH": "PYTHONPATH:/usr/lib/python3/dist-packages:/usr/local/lib/python3.9:/usr/lib/python3.9",
    },
    cmd = ["/usr/local/bin/python3", "run.py"],
    ports = [],
    #entrypoint = "./entrypoint.sh",
    symlinks = { 
    },
    tags = ["manual"],
)