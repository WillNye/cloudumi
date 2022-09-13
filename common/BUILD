load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "models.py",
    ),
    visibility = ["//visibility:public"],
)

copy_file(
    name = "noq_logo_png",
    src = "//frontend/src/assets:NoqLogo.png",
    out = "templates/NoqLogo.png",
    allow_symlink = True,
)

copy_file(
    name = "noq_logo_svg",
    src = "//frontend/src/assets:NoqLogo.svg",
    out = "templates/NoqLogo.svg",
    allow_symlink = True,
)



exports_files(
    ["models.py"],
)

py_library(
    name = "lib",
    data = [
         ":template_files",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = [
        "//common/lib",
        requirement("pydantic"),
    ],
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
