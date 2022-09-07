load("//util:version.bzl", "version")

exports_files(
    srcs = ["upload.py"],
    visibility = ["//visibility:public"],
)

version(
    name="repo_version",
    srcs = ["BUILD"],
)

py_binary(
    name = "upload",
    data = [":repo_version"],
    srcs_version = "PY3",
    srcs = [
        "upload.py",
    ],
    env = {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "noq_prod",
    },
    visibility = ["//visibility:public"],
)
