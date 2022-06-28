load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_library(
    name = "test_files",
    srcs = glob(["test_*.py"]),
    visibility = ["//visibility:public"],
)

# pytest_test(
#     name = "test_accessui",
#     data = [
#         "//util/tests:configs",
#     ],
#     srcs = [
#         "test_accessui.py",
#     ],
#     deps = [
#         "//util/tests:test_dependencies_lib",
#     ],
# )

pytest_test(
    name = "test_base",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_base.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_policies_handlers",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_policies_handlers.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_role_login_api",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_role_login_api.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

# pytest_test(
#     name = "test_users",
#     data = [
#         "//util/tests:configs",
#     ],
#     srcs = [
#         "test_users.py",
#     ],
#     deps = [
#         "//util/tests:test_dependencies_lib",
#     ],
# )
