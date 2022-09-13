load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "template_files",
    srcs = glob([
        "*.j2",
    ]) + [
        ":noq_logo_png",
        ":noq_logo_svg",
    ],
    visibility = ["//visibility:public"],
)

copy_file(
    name = "noq_logo_png",
    src = "//frontend/src/assets:NoqLogo.png",
    out = "NoqLogo.png",
    allow_symlink = True,
    visibility = ["//visibility:public"],
)

copy_file(
    name = "noq_logo_svg",
    src = "//frontend/src/assets:NoqLogo.svg",
    out = "NoqLogo.svg",
    allow_symlink = True,
    visibility = ["//visibility:public"],
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
