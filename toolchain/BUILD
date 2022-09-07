# build/toolchains/BUILD.bazel
load(":dummy_toolchain.bzl", "dummy_toolchain")

dummy_toolchain(
    name = "dummy_toolchain",
)

toolchain(
    name = "macos_dummy_cpp_toolchain",
    exec_compatible_with = [
        "@platforms//os:macos",
    ],
    target_compatible_with = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
    toolchain = ":dummy_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)
