load("@version//:repo_version.bzl", "VersionInfoProvider")
load("@rules_nodejs//nodejs:providers.bzl", "DeclarationInfo", "JSModuleInfo", "STAMP_ATTR")
load("@build_bazel_rules_nodejs//:providers.bzl", "ExternalNpmPackageInfo", "node_modules_aspect", "run_node")
load("@build_bazel_rules_nodejs//internal/common:expand_variables.bzl", "expand_variables")
load("@build_bazel_rules_nodejs//internal/linker:link_node_modules.bzl", "module_mappings_aspect")

####
# This is mostly copied from https://github.com/bazelbuild/rules_nodejs/blob/stable/internal/node/npm_package_bin.bzl
# with the addition of pulling in the version info from the version repository rule
####

_ATTRS = {
    "args": attr.string_list(mandatory = True),
    "base_url": attr.string(mandatory = True),
    "chdir": attr.string(),
    "configuration_env_vars": attr.string_list(default = []),
    "data": attr.label_list(allow_files = True, aspects = [module_mappings_aspect, node_modules_aspect]),
    "deps": attr.label_list(
        providers = [VersionInfoProvider],
        doc = "Dependencies that provide version information",
    ),
    "env": attr.string_dict(default = {}),
    "exit_code_out": attr.output(),
    "link_workspace_root": attr.bool(),
    "output_dir": attr.bool(),
    "outs": attr.output_list(),
    "silent_on_success": attr.bool(),
    "stderr": attr.output(),
    "stdout": attr.output(),
    "tool": attr.label(
        executable = True,
        cfg = "exec",
        mandatory = True,
    ),
    "stamp": STAMP_ATTR,
}

def _expand_locations(ctx, s):
    # `.split(" ")` is a work-around https://github.com/bazelbuild/bazel/issues/10309
    # _expand_locations returns an array of args to support $(execpaths) expansions.
    # TODO: If the string has intentional spaces or if one or more of the expanded file
    # locations has a space in the name, we will incorrectly split it into multiple arguments
    return ctx.expand_location(s, targets = ctx.attr.data).split(" ")

def _inputs(ctx):
    # Also include files from npm fine grained deps as inputs.
    # These deps are identified by the ExternalNpmPackageInfo provider.
    inputs_depsets = []
    for d in ctx.attr.data:
        if ExternalNpmPackageInfo in d:
            inputs_depsets.append(d[ExternalNpmPackageInfo].sources)
        if JSModuleInfo in d:
            inputs_depsets.append(d[JSModuleInfo].sources)
        if DeclarationInfo in d:
            inputs_depsets.append(d[DeclarationInfo].declarations)
    return depset(ctx.files.data, transitive = inputs_depsets).to_list()

def _node_scripts_impl(ctx):
    deps = [dep[VersionInfoProvider] for dep in ctx.attr.deps]
    if len(deps) == 1:
        version = deps[0].version
        branch = deps[0].branch
    else:
        version = "0.0.0-dev.local"
        branch = "local"

    envs = {}
    for k, v in ctx.attr.env.items():
        envs[k] = " ".join([expand_variables(ctx, e, outs = ctx.outputs.outs, output_dir = ctx.attr.output_dir, attribute_name = "env") for e in _expand_locations(ctx, v)])

    envs["PUBLIC_URL"] = "%s/%s/%s" % (ctx.attr.base_url, branch, version)

    if ctx.attr.output_dir and ctx.outputs.outs:
        fail("Only one of output_dir and outs may be specified")
    if not ctx.attr.output_dir and not len(ctx.outputs.outs) and not ctx.attr.stdout and not ctx.attr.stderr:
        fail("One of output_dir, outs, stdout or stderr must be specified")

    args = ctx.actions.args()
    inputs = _inputs(ctx)
    outputs = []

    if ctx.attr.output_dir:
        outputs = [ctx.actions.declare_directory(ctx.attr.name)]
    else:
        outputs = ctx.outputs.outs

    for a in ctx.attr.args:
        args.add_all([expand_variables(ctx, e, outs = ctx.outputs.outs, output_dir = ctx.attr.output_dir) for e in _expand_locations(ctx, a)])

    tool_outputs = []
    if ctx.outputs.stdout:
        tool_outputs.append(ctx.outputs.stdout)

    if ctx.outputs.stderr:
        tool_outputs.append(ctx.outputs.stderr)

    if ctx.outputs.exit_code_out:
        tool_outputs.append(ctx.outputs.exit_code_out)

    run_node(
        ctx,
        executable = "tool",
        inputs = inputs,
        outputs = outputs,
        arguments = [args],
        configuration_env_vars = ctx.attr.configuration_env_vars,
        chdir = expand_variables(ctx, ctx.attr.chdir),
        env = envs,
        stdout = ctx.outputs.stdout,
        stderr = ctx.outputs.stderr,
        exit_code_out = ctx.outputs.exit_code_out,
        silent_on_success = ctx.attr.silent_on_success,
        link_workspace_root = ctx.attr.link_workspace_root,
        mnemonic = "NpmPackageBin",
    )
    files = outputs + tool_outputs
    return [DefaultInfo(
        files = depset(files),
        runfiles = ctx.runfiles(files = files),
    )]

node_scripts = rule(
    implementation = _node_scripts_impl,
    attrs = _ATTRS,
)

def react_scripts(name, args, **kwargs):
    node_scripts(
        name = name,
        tool = "@npm//react-scripts/bin:react-scripts",
        args = args,
        **kwargs
    )
