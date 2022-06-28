load("//util/tests:defs.bzl", "pytest_test")

pytest_test(
    name = "tests",
    deps = [
        "//common/tests:test_files",
        "//common/lib/cognito/tests:test_files",
        "//common/config/tests:test_files",
        "//util/tests:test_dependencies_lib",
    ],
    whitelist = [
        "common",
        "api",
    ],
)
