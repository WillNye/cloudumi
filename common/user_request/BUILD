load("@rules_python//python:packaging.bzl", "py_wheel")

filegroup(
    name = "src_files",
    srcs = glob([
        "**/*.py"
    ]),
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "py_wheel",
    distribution = "common_lib",
    python_tag = "py3",
    version = "$(VERSION)",
    deps = [":lib"],
    tags = ["manual"],
)