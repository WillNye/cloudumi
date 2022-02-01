load("@npm//@bazel/typescript:index.bzl", "ts_project")
load("@npm//http-server:index.bzl", "http_server")
load("@npm//sass:index.bzl", "sass")
load("@npm//webpack-cli:index.bzl", webpack = "webpack_cli")

filegroup(
    name = "src",
    srcs = glob([
        "assets/**/*",
        "auth/**/*",
        "components/**/*",
        "helpers/**/*",
        "semantic-ui/**/*",
        "*.js",
        "*.css",
        "*.svg",
    ]),
    visibility = ["//visibility:public"],
)

# Example if we want to sass it up
# sass(
#     name = "styles",
#     outs = ["styles.css"],
#     args = [
#         "$(execpath styles.scss)",
#         "$(execpath styles.css)",
#     ],
#     data = ["styles.scss"],
# )

# Example if we want to use typescript at some point
# ts_project(
#     # Experimental: Start a tsc daemon to watch for changes to make recompiles faster.
#     supports_workers = True,
#     deps = [
#         "@npm//@types",
#         "@npm//csstype",
#     ],
# )

# webpack(
#     name = "bundle",
#     outs = ["app.bundle.js"],
#     args = [
#         "index.js",
#         "--config",
#         "webpack.config.js",
#         "-o",
#         "$@",
#     ],
#     data = [
#         "index.js",
#         "webpack.config.js",
#         "@npm//:node_modules",
#     ],
# )

webpack(
    name = "bundle",
    outs = ["app.bundle.js"],
    args = [
        "$(execpath index.js)",
        "--config",
        "$(execpath webpack.config.js)",
        "-o",
        "$@",
    ],
    data = [
        "index.js",
        # "somestyles.css",
        # "styles.css",
        "webpack.config.js",
        "@npm//:node_modules",
        ":src",
    ],
    deps = [
        ":src",
    ]
)

# Note, on Windows you need `--enable_runfiles`
http_server(
    name = "server",
    data = [
        "app.bundle.js",
        "index.html",
    ],
    templated_args = ["."],
)