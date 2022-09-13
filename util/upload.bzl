load("@version//:repo_version.bzl", "VersionInfoProvider")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

_ATTRS = {
    "bucket_name": attr.string(
        doc = "Name to the bucket to upload the CDN files to",
    ),
    "data": attr.label(
        allow_files = True,
        mandatory = True,
        doc = "The files to upload to the CDN",
    ),
    "deps": attr.label_list(
        #providers = [VersionInfoProvider],
        mandatory = True,
        doc = "Version info from the version repository rule",
    ),
}

def _upload_cdn_impl(ctx):
    """Implementation of the upload_cdn rule."""
    # Get the version info from the version repository.
    # DEBUG: /home/matt/dev/noq/cloudumi/util/upload.bzl:35:10: <target @cloudumi_python_ext_awscli//:pkg, keys:[PyInfo, InstrumentedFilesInfo, PyCcLinkParamsProvider, OutputGroupInfo]>
    if not ctx.attr.deps:
        fail("No version info found. Please add a version repository rule to your WORKSPACE file and reference it in the deps")
    version_info = VersionInfoProvider()
    for dep in ctx.attr.deps:
        if VersionInfoProvider in dep:
            version_info = dep[VersionInfoProvider]
        else:
            awscli = dep.files.to_list()[0].path + "/dist/aws"

    version = version_info.version
    branch = version_info.branch

    files = ctx.attr.data.files
    output_file = ctx.actions.declare_file(ctx.label.name)

    # Get the base URL.
    bucket_path = "s3://{bucket_name}/{version}/{branch}".format(
        bucket_name = ctx.attr.bucket_name,
        version = version,
        branch = branch,
    )

    output = []
    output.append("Bucket Path: {bucket_path}".format(bucket_path = bucket_path))

    ctx.actions.run_shell(
        inputs = files,
        outputs = [output_file],
        command = "{aws} s3 sync {build_output} {bucket_path} >> {output_file}".format(
            aws = awscli,
            build_output = ctx.attr.data.files.to_list()[0].path,
            bucket_path = bucket_path,
            output_file = output_file.path,
        ),
        use_default_shell_env = True,
    )

    return DefaultInfo(files = depset([output_file]))


upload_cdn = rule(
    implementation = _upload_cdn_impl,
    attrs = _ATTRS,
)
