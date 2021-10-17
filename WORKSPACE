
workspace(name = "cloudumi")

# To download http stuff
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# Python build rules: https://github.com/bazelbuild/rules_python
http_archive(
    name = "rules_python",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.3.0/rules_python-0.3.0.tar.gz",
    sha256 = "934c9ceb552e84577b0faf1e5a2f0450314985b4d8712b2b70717dc679fdc01b",
)

http_archive(
    name = "io_bazel_rules_docker",
    sha256 = "1f4e59843b61981a96835dc4ac377ad4da9f8c334ebe5e0bb3f58f80c09735f4",
    strip_prefix = "rules_docker-0.19.0",
    urls = ["https://github.com/bazelbuild/rules_docker/releases/download/v0.19.0/rules_docker-v0.19.0.tar.gz"],
)

http_archive(
    name = "rules_proto_grpc",
    sha256 = "4202a150910712d00d95f11e240ad6da4c92e542d3b9fbb5b3a3d60abba3de77",
    strip_prefix = "rules_proto_grpc-4.0.0",
    urls = ["https://github.com/rules-proto-grpc/rules_proto_grpc/archive/4.0.0.tar.gz"],
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

# The Alpine container is primarily for testing
container_pull(
  architecture = "amd64",
  name = "python_alpine_base_amd64",
  registry = "index.docker.io",
  repository = "library/python",
  tag = "3-alpine",
  # digest = "sha256:1f7d284b9480f13289d42dc6a19a5be292dcfc2b9bc60916d1bccb8791177874"
)

# This will be the cloudumi_base_docker container
container_pull(
    architecture = "amd64",
    name = "python_3.9.7_container",
    registry = "index.docker.io",
    repository = "library/python",
    tag = "3.9.7",
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
load("@nexus_python_ext//:requirements.bzl", "install_deps")
# Call it to define repos for your requirements.
install_deps()

# Proto and Grpc build stuff: https://github.com/rules-proto-grpc/rules_proto_grpc
load("@rules_proto_grpc//:repositories.bzl", "rules_proto_grpc_toolchains", "rules_proto_grpc_repos")
rules_proto_grpc_toolchains()
rules_proto_grpc_repos()

load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies", "rules_proto_toolchains")
rules_proto_dependencies()
rules_proto_toolchains()

load("@rules_proto_grpc//python:repositories.bzl", rules_proto_grpc_python_repos = "python_repos")
rules_proto_grpc_python_repos()
load("@com_github_grpc_grpc//bazel:grpc_deps.bzl", "grpc_deps")
grpc_deps()
