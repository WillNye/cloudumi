filegroup(
    name = "template_files",
    srcs = glob([
        "*.j2",
    ]) + [
        "//common:noq_logo_png",
        "//common:noq_logo_svg",
    ],
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
