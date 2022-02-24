load("@rules_python//python:defs.bzl", "py_binary")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_binary(
    name = "populate_services",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        "populate_services.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        requirement("asgiref"),
    ],
    visibility = ["//visibility:public"],
)

genrule(
    name = "containers-dev",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           -f deploy/docker-compose-bazel-containers.yaml \
           up -d' &>$@",
    executable = True,
    outs = [
        "running",
    ],
    exec_tools = [
        "//api:container-dev-local",
        "//common/celery_tasks:container-dev-local",
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)

genrule(
    name = "containers-dev-kill",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           -f deploy/docker-compose-bazel-containers.yaml \
           down -v' &>$@",
    executable = True,
    outs = [
        "removed",
    ],
    srcs = [
        "//api:container-dev-local",
        "//common/celery_tasks:container-dev-local",
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)

genrule(
    name = "deps-only",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           up -d' &>$@",
    executable = True,
    outs = [
        "_running-deps-only_",
    ],
    exec_tools = [
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)

genrule(
    name = "kill-deps-only",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           down -v' &>$@",
    executable = True,
    outs = [
        "_kill-deps-only_",
    ],
    exec_tools = [
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)
