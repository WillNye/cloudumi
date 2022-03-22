load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

pytest_test(
    name = "test_celery",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_celery.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)
