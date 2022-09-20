load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")

INT_DEPS = [
]

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
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
    deps = INT_DEPS + [
    ],
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "py_wheel",
    distribution = "cloudumi_plugin_lib",
    python_tag = "py3",
    version = "$(VERSION)",
    deps = INT_DEPS + [":lib"],
    tags = ["manual"],
)