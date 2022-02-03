workspace(name = "cloudumi")

# To download http stuff
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# Python build rules: https://github.com/bazelbuild/rules_python
http_archive(
    name = "rules_python",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.5.0/rules_python-0.5.0.tar.gz",
    sha256 = "cd6730ed53a002c56ce4e2f396ba3b3be262fd7cb68339f0377a45e8227fe332",
)

http_archive(
    name = "io_bazel_rules_docker",
    sha256 = "85ffff62a4c22a74dbd98d05da6cf40f497344b3dbf1e1ab0a37ab2a1a6ca014",
    strip_prefix = "rules_docker-0.23.0",
    urls = ["https://github.com/bazelbuild/rules_docker/releases/download/v0.23.0/rules_docker-v0.23.0.tar.gz"],
)

http_archive(
    name = "rules_proto_grpc",
    sha256 = "8383116d4c505e93fd58369841814acc3f25bdb906887a2023980d8f49a0b95b",
    strip_prefix = "rules_proto_grpc-4.1.0",
    urls = ["https://github.com/rules-proto-grpc/rules_proto_grpc/archive/4.1.0.tar.gz"],
)

http_archive(
    name = "build_bazel_rules_nodejs",
    sha256 = "c077680a307eb88f3e62b0b662c2e9c6315319385bc8c637a861ffdbed8ca247",
    urls = ["https://github.com/bazelbuild/rules_nodejs/releases/download/5.1.0/rules_nodejs-5.1.0.tar.gz"],
)

load("@build_bazel_rules_nodejs//:repositories.bzl", "build_bazel_rules_nodejs_dependencies")
build_bazel_rules_nodejs_dependencies()

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
    name = "python_3.9.7_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/python",
    digest = "sha256:ff27cd87bc7dbdb5e4f413d4e09d04cb59499457dff85c02055a9b93196c7804",
    # tag = "3.9.7",
)

container_pull(
    name = "python_3.9.7_alpine_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/python",
    tag = "3.9.7-alpine",
)

# This is the default image to make sure xmlsec works
container_pull(
    name = "python_3.8.12_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/python",
    digest = "sha256:a874dcabc74ca202b92b826521ff79dede61caca00ceab0b65024e895baceb58",
    # tag = "3.8.12",
)

container_pull(
    name = "python_3.8.12_alpine_container",
    architecture = "amd64",
    registry = "index.docker.io",
    repository = "library/python",
    tag = "3.8.12-alpine",
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
