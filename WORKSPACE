workspace(name = "cloudumi")

# To download http stuff
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")

### PKG Rules - notice order matters here because Python brings it own rules_pkg
http_archive(
    name = "rules_pkg",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_pkg/releases/download/0.7.0/rules_pkg-0.7.0.tar.gz",
        "https://github.com/bazelbuild/rules_pkg/releases/download/0.7.0/rules_pkg-0.7.0.tar.gz",
    ],
    sha256 = "8a298e832762eda1830597d64fe7db58178aa84cd5926d76d5b744d6558941c2",
)
load("@rules_pkg//:deps.bzl", "rules_pkg_dependencies")
rules_pkg_dependencies()

# Python build rules: https://github.com/bazelbuild/rules_python
http_archive(
    name = "rules_python",
    sha256 = "b593d13bb43c94ce94b483c2858e53a9b811f6f10e1e0eedc61073bd90e58d9c",
    strip_prefix = "rules_python-0.12.0",
    url = "https://github.com/bazelbuild/rules_python/archive/refs/tags/0.12.0.tar.gz",
)
load("@rules_python//python:repositories.bzl", "python_register_toolchains")

http_archive(
    name = "bazel_skylib",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/1.3.0/bazel-skylib-1.3.0.tar.gz",
        "https://github.com/bazelbuild/bazel-skylib/releases/download/1.3.0/bazel-skylib-1.3.0.tar.gz",
    ],
    sha256 = "74d544d96f4a5bb630d465ca8bbcfe231e3594e5aae57e1edbf17a6eb3ca2506",
)
load("@bazel_skylib//:workspace.bzl", "bazel_skylib_workspace")
bazel_skylib_workspace()

python_register_toolchains(
    name = "python3_10",
    # Available versions are listed in @rules_python//python:versions.bzl.
    # We recommend using the same version your team is already standardized on.
    python_version = "3.10",
)

load("@python3_10//:defs.bzl", "interpreter")

# Setup Python Configuration to include a central pip repo
load("@rules_python//python:pip.bzl", "pip_parse")

# Create a central repo that knows about the dependencies needed from
# requirements_lock.txt.
pip_parse(
    name = "cloudumi_python_ext",
    python_interpreter_target = interpreter,
    requirements_lock = "//:requirements.lock",
)

# Load the starlark macro which will define your dependencies.
load("@cloudumi_python_ext//:requirements.bzl", "install_deps")

# Call it to define repos for your requirements.
install_deps()

### DOCKER
http_archive(
    name = "io_bazel_rules_docker",
    sha256 = "b1e80761a8a8243d03ebca8845e9cc1ba6c82ce7c5179ce2b295cd36f7e394bf",
    urls = ["https://github.com/bazelbuild/rules_docker/releases/download/v0.25.0/rules_docker-v0.25.0.tar.gz"],
)

# Setup Docker stuff
load(
    "@io_bazel_rules_docker//repositories:repositories.bzl",
    container_repositories = "repositories",
)

container_repositories()

load(
    "@io_bazel_rules_docker//python3:image.bzl",
    _py3_image_repos = "repositories",
)

_py3_image_repos()

## Docker stuff: load containers
load(
    "@io_bazel_rules_docker//container:container.bzl",
    "container_pull",
)

# Redis container
container_pull(
    name = "cloudumi_redis",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/redis",
    tag = "alpine",
)

# This will be the cloudumi_base_docker container
container_pull(
    name = "python_3.10_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/python",
    digest = "sha256:8d1f943ceaaf3b3ce05df5c0926e7958836b048b700176bf9c56d8f37ac13fca",
    tag = "3.10.6",
)

container_pull(
    name = "nodejs_17_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/node",
    digest = "sha256:13961fc7673e7a62de914c59783364087038d03dc274ed720e9eae868cd422d5",
    tag = "17-alpine",
)

container_pull(
    name = "nginx_1.20_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/nginx",
    digest = "sha256:a67c36aaec8f2ac2e7cc83bc107dcac428ad4803c72be4710669039ab549cd24",
    tag = "1.20",
)

### gRPC
http_archive(
    name = "rules_proto_grpc",
    strip_prefix = "rules_proto_grpc-4.2.0",
    urls = ["https://github.com/rules-proto-grpc/rules_proto_grpc/archive/4.2.0.tar.gz"],
    sha256 = "bbe4db93499f5c9414926e46f9e35016999a4e9f6e3522482d3760dc61011070",
)

# Proto and Grpc build stuff: https://github.com/rules-proto-grpc/rules_proto_grpc
load("@rules_proto_grpc//:repositories.bzl", "rules_proto_grpc_repos", "rules_proto_grpc_toolchains")

rules_proto_grpc_toolchains()

rules_proto_grpc_repos()

load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies", "rules_proto_toolchains")

rules_proto_dependencies()

rules_proto_toolchains()

load("@rules_proto_grpc//python:repositories.bzl", rules_proto_grpc_python_repos = "python_repos")

rules_proto_grpc_python_repos()

load("@com_github_grpc_grpc//bazel:grpc_deps.bzl", "grpc_deps")

grpc_deps()

### NodeJS
http_archive(
    name = "build_bazel_rules_nodejs",
    sha256 = "f10a3a12894fc3c9bf578ee5a5691769f6805c4be84359681a785a0c12e8d2b6",
    urls = ["https://github.com/bazelbuild/rules_nodejs/releases/download/5.5.3/rules_nodejs-5.5.3.tar.gz"],
)

load("@build_bazel_rules_nodejs//:repositories.bzl", "build_bazel_rules_nodejs_dependencies")
build_bazel_rules_nodejs_dependencies()

load(
    "@io_bazel_rules_docker//nodejs:image.bzl",
    _nodejs_image_repos = "repositories",
)

_nodejs_image_repos()
# fetches nodejs, npm, and yarn
load("@build_bazel_rules_nodejs//:index.bzl", "node_repositories", "yarn_install")
node_repositories()
yarn_install(
    name = "npm",
    package_json = "//frontend:package.json",
    yarn_lock = "//frontend:yarn.lock",
    links = {
        "target": "//frontend",
    },
)

# Weep
http_file(
    name = "weep",
    downloaded_file_path = "weep",
    executable = True,
    url = "https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_x86_64/weep",
    sha256 = "532004cb40f48d5c8b7f37db87ea41e82619376e72761e1e9657dde63d1fae19",
)

register_toolchains(
    "//toolchain:macos_dummy_cpp_toolchain",
)

load("//util:version.bzl", "get_repo_version")
get_repo_version(name="version")


http_archive(
    name = "awscli",
    url = "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip",
    sha256 = "ca0e766fe70b14c1f7e2817836acf03e4a3e6391b7ed6a464282c5b174580b9a",
    build_file = "@//util:awscli.BUILD",
)

