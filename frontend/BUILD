load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@build_bazel_rules_nodejs//:index.bzl", "copy_to_bin", "nodejs_test")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")
load("@io_bazel_rules_docker//docker/util:run.bzl", "container_run_and_commit")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
#load("@io_bazel_rules_docker//nodejs:image.bzl", "nodejs_image")
load("@npm//react-scripts:index.bzl", "react_scripts", "react_scripts_test")

# Filename conventions described at
# https://create-react-app.dev/docs/running-tests#filename-conventions
_TESTS = []  # For later

filegroup(
    name = "nginx_config_file",
    srcs = ["nginx/default.conf"],
)

# We don't want to teach react-scripts to include from multiple directories
# So we copy everything it wants to read to the output "bin" directory
copy_to_bin(
    name = "copy_static_files",
    srcs = glob(
        [
            "public/**/*",
            "src/**/*",
        ],
        exclude = _TESTS + [
        ],
    ) + [
        "//frontend/src/assets",
        "jsconfig.json",
        "package.json",
        "yarn.lock",
        ".eslintrc",
        ".eslintignore",
    ],
)

# react-scripts can only work if the working directory is the root of the application.
# So we'll need to chdir before it runs.
write_file(
    name = "write_chdir_script",
    out = "chdir.cjs",
    content = ["process.chdir(__dirname)"],
)

_RUNTIME_DEPS = [
    "chdir.cjs",
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
    "@npm//@sentry/react",
    "@npm//@sentry/tracing",
    "@npm//survey-react",
    "@npm//yaml",
    "@npm//eslint-config-react-app",
    "@npm//babel-eslint",
    "@npm//eslint",
    "@npm//eslint-config-prettier",
    "@npm//eslint-plugin-flowtype",
    "@npm//eslint-plugin-import",
    "@npm//eslint-plugin-jsx-a11y",
    "@npm//eslint-plugin-react",
    "@npm//eslint-plugin-react-hooks",
    "@npm//zustand",
    "@npm//use-state-if-mounted",
    "@npm//sass"
]

_DEV_DEPS = [
    "@npm//react-scripts",
]

genrule(
   name = "upload",
   srcs = glob(["./build/**"]),
   cmds = "aws s3 sync frontend/dist/ $BUCKETPATH",
   deps = ["//frontend:build"]
)

react_scripts(
    # Note: If you want to change the name make sure you update BUILD_PATH below accordingly
    # https://create-react-app.dev/docs/advanced-configuration/
    name = "build",
    args = [
        "--node_options=--require=./$(execpath chdir.cjs)",
        "build",
    ],
    data = _RUNTIME_DEPS,
    env = {
        "BUILD_PATH": "./build",
        "DISABLE_ESLINT_PLUGIN": "true"
    },
    output_dir = True,
    visibility = ["//visibility:public"],
)

react_scripts(
    name = "start",
    args = [
        "--node_options=--require=./$(rootpath chdir.cjs)",
        "start",
    ],
    env = {
        "DISABLE_ESLINT_PLUGIN": "true",
        "FRONTEND_SENTRY_DSN": "https://5f3b026abb7649fe8b41e903dcb5820f@sentry.noq.dev:4443/2"
    },
    data = _RUNTIME_DEPS,
    tags = [
        # This tag instructs ibazel to pipe into stdin a event describing actions.
        # ibazel send EOF to stdin by default and `react-scripts start` will stop when getting EOF in stdin.
        # So use this to prevent EOF.
        "ibazel_notify_changes",
    ],
)

pkg_tar(
    name = "nginx_config",
    srcs = [
        ":nginx_config_file",
    ],
    strip_prefix = "/frontend/nginx",
)

container_layer(
    name = "runtime_deps_layer",
    files = [":build"] + _RUNTIME_DEPS,
    data_path = "/ui",
    directory = "/ui",
)

container_layer(
    name = "dev_deps_layer",
    files = _DEV_DEPS,
    data_path = "/",
    directory = "/",
)

container_layer(
    name = "nginx_config_layer",
    tars = [":nginx_config"],
    directory = "/etc/nginx/conf.d",
)

container_image(
    name = "container-dev-local",
    base = "@nodejs_17_container//image",
    layers = [
        ":dev_deps_layer",
        ":runtime_deps_layer",
    ],
    env = {
        "NODE_PATH": "/npm/node_modules",
    },
    ports = ["80:80"],
    workdir = "/ui/frontend",
    cmd = ["npm", "start"],
)

container_image(
    name = "container",
    base = "@nginx_1.20_container//image",
    layers = [
        ":nginx_config_layer",
        ":runtime_deps_layer",
    ],
    workdir = "/ui/frontend/build",
    ports = ["80:80"],
    cmd = ["nginx", "-g", "daemon off;"],
)
