# Testing with Pytest (and Coffee)

Regardless of unittest being in use, we use `pytest` to test.

The mono repo, managed by bazel, represents a unique challenge in integrating with `pytest`. In order to have our torte and eat it too, we need to jump through a few hoops. In a shell of nut:

1. All fixtures need to be located in the `fixtures` sub directory from this bazel module.
2. The wrapper script calls pytest for us.
3. In order to have the wrapper script call pytest for us we need the pytest_test rule defined in [defs.bzl](defs.bzl).
4. This works great! As long as it's in bazel. Soooooooooo, like devs just like wanna debug and stuff, soooo: we create a wheel target that can be imported into a venv in order to facilitate the loading of fixtures.py

Magic? Yes.

## Ground rules

- Add unit tests close to their bazel module - so for instance, unit tests for the `common/config` bazel module should have tests in `common/config/tests`
- Add any additional fixtures **only** in `/util/pytest/fixtures/` as a submodule (see #developing-new-fixtures--test-stuff)

## Test with VSCODE | command line

- Make sure you run VSCODE as follows: `PYTHONPATH=$(pwd) code .` from your cloudumi repo
- Ensure you have the following settings in your workspace settings (should be checked in under .vscode) // "functional_tests",:
- Use the `Debug: Unit Tests` configuration in launch.json to run tests in VSCODE

Here is the .env file content:

```json
PYTHONPATH="/home/matt/dev/cloudumi"
AWS_REGION="us-east-1"
AWS_PROFILE="development/NoqSaasRoleLocalDev"
# CONFIG_LOCATION="/home/matt/dev/cloudumi/configs/development_account/saas_development.yaml"  -- Use this for functional tests
CONFIG_LOCATION="/home/matt/dev/cloudumi/util/tests/test_configuration.yaml"
TEST_USER_DOMAIN="localhost"
ASYNC_TEST_TIMEOUT=120
PYTHONDONTWRITEBYTECODE=1
PYTEST_PLUGINS=util.tests.fixtures.fixtures
AWS_DEFAULT_REGION=us-east-1
```

Obviously, change `/path/to/cloudumi` to be the absolute path on your system to the root of the cloudumi mono repo

For VSCODE, these are all one-time setup instructions. _This is important_ in VSCODE, do **NOT** select `python configure tests` as it will overwrite the workspace settings.json file.

## Developing new fixtures / test stuff

- In fixtures, update the fixtures.py file, or add any additional plugins
