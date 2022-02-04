load("@build_bazel_rules_nodejs//:index.bzl", "copy_to_bin", "nodejs_binary", "npm_package_bin")
load("@npm//http-server:index.bzl", "http_server")
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

exports_files(
    srcs = [
        "index.js",
        "webpack.config.js",
    ],
    visibility = ["//visibility:public"],
)

copy_to_bin(
    name = "source_files_in_bin",
    srcs = [
        ":src",
    ],
)

webpack(
    name = "bundle",
    outs = ["app.bundle.js"],
    args = [
        "bundle",
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
        ":source_files_in_bin",
        ":src",
    ],
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