# Testing with Pytest (and Coffee)

Regardless of unittest being in use, we use `pytest` to test.

The mono repo, managed by bazel, represents a unique challenge in integrating with `pytest`. In order to have our torte and eat it too, we need to jump through a few hoops. In a shell of nut:

1. All fixtures need to be located in the `fixtures` sub directory from this bazel module.
2. The wrapper script calls pytest for us.
3. In order to have the wrapper script call pytest for us we need the pytest_test rule defined in [defs.bzl](defs.bzl).
4. This works great! As long as it's in bazel. Soooooooooo, like devs just like wanna debug and stuff, soooo: we create a wheel target that can be imported into a venv in order to facilitate the loading of conftest.py

Magic? Yes.

## Ground rules

- Add unit tests close to their bazel module - so for instance, unit tests for the `common/config` bazel module should have tests in `common/config/tests`
- Add any additional fixtures **only** in `/util/pytest/fixtures/` as a submodule (see #developing-new-fixtures--test-stuff)

## Test with bazel

- `bazel test //...` - runs all tests discovered
- `bazel test //api/...` - runs all API tests
- `bazel test //common/config:test_ip_restriction` - runs a specific test

## Test with VSCODE

- Build the cloudumi pytest utility: `bazel build //util/pytest:wheel`
- Note the path to the wheel file in the output (for instance: `bazel-bin/util/pytest/cloudumi_fixtures-0.0.1-py3-none-any.whl`)
- Make sure you are in your venv
- `pip install <output - ie. bazel-bin/util/pytest/cloudumi_fixtures-0.0.1-py3-none-any.whl>`
- Ensure you have the following settings in your workspace settings (should be checked in under .vscode):

```json
{
  "python.formatting.provider": "black",
  "python.testing.pytestArgs": [
    "-pfixtures.conftest",
    "api",
    "common",
    "identity",
    "plugins",
    "util"
  ],
  "python.envFile": "${workspaceFolder}/.env",
  "python.testing.unittestEnabled": false,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestArgs": ["-v", "-s", "./common", "-p", "test_*.py"]
}
```

For VSCODE, these are all one-time setup instructions. _This is important_ in VSCODE, do **NOT** select `python configure tests` as it will overwrite the workspace settings.json file.

## Developing new fixtures / test stuff

- In fixtures, update the conftest.py file, or add any additional plugins
- Any additional plugins must be referenced here:
  - `fixtures/BUILD` (in exports_files)
  - `BUILD` (py_library/srcs - follow the example of conftest)
