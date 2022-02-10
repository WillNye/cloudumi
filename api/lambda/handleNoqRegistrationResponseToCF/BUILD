load("@cloudumi_python_ext//:requirements.bzl", "requirement", "whl_requirement")
load("@rules_pkg//:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mklink")
load("@rules_pkg//:pkg.bzl", "pkg_zip")
load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package")

py_library(
    name = "lib",
    deps = [
        requirement("requests"),
    ],
    srcs = [
        "handler.py",
    ],
)

genrule(
    name = "bundle",
    srcs = [
        ":lib",
        ":requirements.txt",
    ],
    cmd = "pip install --target $(RULEDIR) -r $(location :requirements.txt) >$@",
    executable = False,
    outs = ["run_bundle"],
    message = "Bundling Lambda",
)

pkg_zip(
    name = "zip",
    srcs = [
        ":bundle",
    ],
)