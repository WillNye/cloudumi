workspace(name = "cloudumi")

# To download http stuff
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

### PKG Rules - notice order matters here because Python brings it own rules_pkg
http_archive(
    name = "rules_pkg",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_pkg/releases/download/0.6.0/rules_pkg-0.6.0.tar.gz",
        "https://github.com/bazelbuild/rules_pkg/releases/download/0.6.0/rules_pkg-0.6.0.tar.gz",
    ],
    sha256 = "62eeb544ff1ef41d786e329e1536c1d541bb9bcad27ae984d57f18f314018e66",
)
load("@rules_pkg//:deps.bzl", "rules_pkg_dependencies")
rules_pkg_dependencies()

# Python build rules: https://github.com/bazelbuild/rules_python
http_archive(
    name = "rules_python",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.5.0/rules_python-0.5.0.tar.gz",
    sha256 = "cd6730ed53a002c56ce4e2f396ba3b3be262fd7cb68339f0377a45e8227fe332",
)

# Setup Python Configuration to include a central pip repo
load("@rules_python//python:pip.bzl", "pip_parse")

# Create a central repo that knows about the dependencies needed from
# requirements_lock.txt.
pip_parse(
    name = "cloudumi_python_ext",
    requirements_lock = "//:requirements.lock",
)

# Load the starlark macro which will define your dependencies.
load("@cloudumi_python_ext//:requirements.bzl", "install_deps")

# Call it to define repos for your requirements.
install_deps()

### DOCKER
http_archive(
    name = "io_bazel_rules_docker",
    sha256 = "85ffff62a4c22a74dbd98d05da6cf40f497344b3dbf1e1ab0a37ab2a1a6ca014",
    strip_prefix = "rules_docker-0.23.0",
    urls = ["https://github.com/bazelbuild/rules_docker/releases/download/v0.23.0/rules_docker-v0.23.0.tar.gz"],
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
    name = "python_3.9_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/python",
    digest = "sha256:743d52e1c66f456f40d1e673fe580d0ebda7b97a926c81678dedfed2d4a3fd31",
    tag = "3.9.10",
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
    sha256 = "8383116d4c505e93fd58369841814acc3f25bdb906887a2023980d8f49a0b95b",
    strip_prefix = "rules_proto_grpc-4.1.0",
    urls = ["https://github.com/rules-proto-grpc/rules_proto_grpc/archive/4.1.0.tar.gz"],
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
    sha256 = "c077680a307eb88f3e62b0b662c2e9c6315319385bc8c637a861ffdbed8ca247",
    urls = ["https://github.com/bazelbuild/rules_nodejs/releases/download/5.1.0/rules_nodejs-5.1.0.tar.gz"],
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
http_archive(
    name = "netflix_weep",
    sha256 = "8cab1473704035de8674e77b21002130c9cd987e206443c15d2596699285929f",
    urls = ["https://github.com/Netflix/weep/releases/download/v0.3.26/weep_0.3.26_linux_x86_64.tar.gz"],
    strip_prefix = "/bin/linux_amd64",
    build_file_content = """exports_files(['weep'])
visibility=['//visibility:public']"""
    #strip_prefix = "/bin/linux_amd64",
)