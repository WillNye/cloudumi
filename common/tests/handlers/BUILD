load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_library(
    name = "test_files",
    srcs = glob(["test_*.py"]),
    visibility = ["//visibility:public"],
)

pytest_test(
    name = "test_base",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_accessui.py",
        "test_base.py",
        "test_policies_handlers.py",
        "test_role_login_api.py",
        "test_users.py",
    ],
    deps = [
    ],
)
