load("@rules_python//python:defs.bzl", "py_test")

def pytest_test(name, whitelist = [], srcs = [], deps = [], data = [], **kwargs):
    """
    Will run all tests in the mono repo that are whitelisted by the `whitelist` argument.

    If whitelist is empty, no tests will be run. Multiple whitelist parts can be provided, each should
    correpsond to the name of a directory in the mono repo, ideally.

    For instance, specifying `common` will only run tests when the `common` directory is in the path.
    Specifying both `cloudumi` and `common` will only run tests that have both `cloudumi` and `common` directories in the path.
    """
    hardcoded_whitelist = list()
    for part in ["cloudumi", "tests"]:
        if part not in whitelist:
            hardcoded_whitelist.append(part)
    hardcoded_whitelist.extend(whitelist)
    whitelist = ",".join(hardcoded_whitelist)
    py_test(
        name = name,
        srcs = [
            "//util/tests:wrapper.py",
            "//util/tests/fixtures:fixtures.py",
            "//util/tests/fixtures:globals.py",
        ] + srcs,
        main = "//util/tests:wrapper.py",
        args = [whitelist],
        python_version = "PY3",
        srcs_version = "PY3",
        deps = deps,
        env = {
            "AWS_REGION": "us-west-2",
            "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
            "AWS_PROFILE": "noq_cluster_dev",
            "HOME": "~",
        },
        data = [
            "//util/tests:test_configuration.yaml",
        ] + data,
        **kwargs
    )
