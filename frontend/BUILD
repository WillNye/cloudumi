load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@build_bazel_rules_nodejs//:index.bzl", "copy_to_bin", "nodejs_test")
#load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")
load("@io_bazel_rules_docker//nodejs:image.bzl", "nodejs_image")
load("@npm//react-scripts:index.bzl", "react_scripts", "react_scripts_test")

# Filename conventions described at
# https://create-react-app.dev/docs/running-tests#filename-conventions
_TESTS = []  # For later

# We don't want to teach react-scripts to include from multiple directories
# So we copy everything it wants to read to the output "bin" directory
copy_to_bin(
    name = "copy_static_files",
    srcs = glob(
        [
            "public/**/*",
            "src/**/*",
        ],
        exclude = _TESTS,
    ) + [
        "jsconfig.json",
        "package.json",
        "yarn.lock",
    ],
)

# react-scripts can only work if the working directory is the root of the application.
# So we'll need to chdir before it runs.
write_file(
    name = "write_chdir_script",
    out = "chdir.js",
    content = ["process.chdir(__dirname)"],
)

_RUNTIME_DEPS = [
    "chdir.js",
    "copy_static_files",

    "@npm//@monaco-editor/react",
    "@npm//axios",
    "@npm//http-server",
    "@npm//js-cookie",
    "@npm//js-yaml",
    "@npm//json-2-csv",
    "@npm//lodash",
    "@npm//luxon",
    "@npm//qs",
    "@npm//react",
    "@npm//react-code-blocks",
    "@npm//react-dom",
    "@npm//react-ga",
    "@npm//react-hook-form",
    "@npm//react-json-view",
    "@npm//react-markdown",
    "@npm//react-router-dom",
    "@npm//react-semantic-ui-datepickers",
    "@npm//react-table",
    "@npm//react-toastify",
    "@npm//semantic-ui-css",
    "@npm//semantic-ui-react",
    "@npm//survey-react",
    "@npm//yaml",
]

react_scripts(
    # Note: If you want to change the name make sure you update BUILD_PATH below accordingly
    # https://create-react-app.dev/docs/advanced-configuration/
    name = "build",
    args = [
        "--node_options=--require=./$(execpath chdir.js)",
        "build",
    ],
    data = _RUNTIME_DEPS,
    env = {
        "BUILD_PATH": "./build",
    },
    output_dir = True,
)

react_scripts(
    name = "start",
    args = [
        "--node_options=--require=./$(rootpath chdir.js)",
        "start",
    ],
    data = _RUNTIME_DEPS,
    tags = [
        # This tag instructs ibazel to pipe into stdin a event describing actions.
        # ibazel send EOF to stdin by default and `react-scripts start` will stop when getting EOF in stdin.
        # So use this to prevent EOF.
        "ibazel_notify_changes",
    ],
)

nodejs_image(
    name = "container",
    entry_point = "index.js",
    data = [":index.js"] + _RUNTIME_DEPS,
)