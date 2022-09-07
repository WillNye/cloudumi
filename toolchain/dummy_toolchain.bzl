def _dummy_toolchain_impl(ctx):
    """Implementation of the dummy_toolchain rule."""
    return [
        platform_common.ToolchainInfo(),
    ]

dummy_toolchain = rule(
    implementation = _dummy_toolchain_impl,
    doc = """
A rule that can be used to create dummy toolchains, which can be useful when a
toolchain is only optionally required and setting up a real toolchain is hard.
""",
    provides = [platform_common.ToolchainInfo],
)


