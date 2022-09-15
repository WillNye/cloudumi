def _get_repo_version_impl(ctx):
    workspace_dir = str(ctx.path(Label("//:WORKSPACE")).dirname)
    git_version = ctx.execute("git describe --tags --abbrev=0".split(" "), working_directory=workspace_dir)
    git_branch = ctx.execute("git rev-parse --abbrev-ref HEAD".split(" "), working_directory=workspace_dir)
    version = git_version.stdout.strip()
    branch = git_branch.stdout.strip()

    ctx.file(
        "repo_version.bzl",
        content="""VersionInfoProvider = provider(
    doc = "Provides the version of the current build.",
    fields = {
        "version": "The version of the current build.",
        "branch": "The branch of the current build.",
    }
)
def _impl(ctx):
    output = ctx.actions.declare_file("version_info")
    ctx.actions.write(output, "%s %s")
    return VersionInfoProvider(version = "%s", branch = "%s")

repo_version = rule(
    implementation = _impl,
    attrs = {},
)
        """ % (version, branch, version, branch),
    )
    ctx.file(
        "BUILD",
        content = "load(':repo_version.bzl', 'repo_version')\nrepo_version(name = 'git_version_info', visibility=['//visibility:public'])",
    )
    return DefaultInfo()

get_repo_version = repository_rule(
    implementation = _get_repo_version_impl,
    attrs = {},
)
