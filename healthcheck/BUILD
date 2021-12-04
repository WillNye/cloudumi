load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "main.py",
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
    deps = [
        requirement("fastapi"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin",
    data = [
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
    },
    deps = [
        requirement("fastapi"),
        requirement("uvicorn"),
    ],
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_healthcheck",
    python_tag = "py3",
    version = "0.0.1",
    # entry_points = {
    #     "console_scripts": [""],
    # },
    deps = [":lib"],
    requires = ["fastapi"],
    strip_path_prefixes = [
    ],
)

container_layer(
    name = "lib_layer",
    files = [
        ":lib",
    ],
    data_path = ".",
    directory = "/healthcheck",
)

container_layer(
    name = "uvicorn_layer",
    files = [
        requirement("uvicorn"),
    ],
    data_path = ".",
)

container_image(
    name = "container",
    base = "//:cloudumi_base_docker",
    layers = [
        ":lib_layer",
        ":uvicorn_layer",
    ],
    env = {
        "TZ": "America/Los_Angeles",
        "PYTHONPATH": "PYTHONPATH:/usr/lib/python3/dist-packages:/usr/local/lib/python3.9:/usr/lib/python3.9",
    },
    cmd = ["uvicorn", "main:app", "--port=8090", "--host=0.0.0.0", "--reload"],
    ports = ["8090"],
    symlinks = {},
    tags = ["manual"],
)