load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "internal_routes.py",
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
        "//cloudumi_common/cloudumi_plugins/cloudumi_plugins/plugins/internal_routes/handlers:lib",
    ],
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "py_wheel",
    distribution = "cloudumi_common_plugin_internal_routes",
    python_tag = "py3",
    version = "$(VERSION)",
    deps = [":lib"],
    tags = ["manual"],
)
