load("@rules_python//python:defs.bzl", "py_test")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

def pytest_test(name, srcs, deps = [], args = [], data = [], **kwargs):
    """
        Pytest Wrapper to simplify calling pytest for testing
    """
    py_test(
        name = name,
        srcs = [
            "//util/tests:wrapper.py",
            "//util/tests/fixtures:fixtures.py",
            "//util/tests/fixtures:globals.py",
        ] + srcs,
        main = "//util/tests:wrapper.py",
        args = [
            "--capture=no",
            # "--black",
            # "--pylint",
            # "--pylint-rcfile=$(location //util/tests:.pylintrc)",
            # "--mypy",
        ] + args + ["$(location :%s)" % x for x in srcs],
        python_version = "PY3",
        srcs_version = "PY3",
        deps = deps + [
            "//common/celery_tasks:lib",
            requirement("boto3"),
            requirement("pytest"),
            requirement("pytest-asyncio"),
            #requirement("pytest-black"),
            #requirement("pytest-pylint"),
            requirement("redislite"),
            requirement("requests-mock"),
            # requirement("pytest-mypy"),
        ],
        env = {
            "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
        },
        data = [
            "//util/tests:.pylintrc",
            "//util/tests:test_configuration.yaml",
        ] + data,
        **kwargs
    )
