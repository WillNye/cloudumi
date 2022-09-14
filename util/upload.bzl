load("@version//:repo_version.bzl", "VersionInfoProvider")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@python3_10//:defs.bzl", "interpreter")

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
    "env": attr.string_dict(
        doc = "Environment variables to pass to the upload script",
    ),
    "interpreter": attr.label(
        default = interpreter,
        allow_files = True,
        cfg = "exec",
        executable = True,
        doc = "The Python interpreter to use to run the upload script",
    ),
    "aws_with_deps": attr.label_list(
        default = [
            requirement("awscli"),
            requirement("botocore"),
            requirement("colorama"),
            requirement("docutils"),
            requirement("jmespath"),
            requirement("six"),
            requirement("urllib3"),
            requirement("pyasn1"),
            requirement("python-dateutil"),
            requirement("pyyaml"),
            requirement("s3transfer"),
            requirement("rsa"),
        ],
        allow_files = True,
        cfg = "target",
        doc = "The awscli package to use to run the upload script",
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
    env = {x: y for x, y in ctx.attr.env.items()}

    for dep in ctx.attr.aws_with_deps:
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = dep.files.to_list()[0].dirname
        else:
            env["PYTHONPATH"] = env["PYTHONPATH"] + ":" + dep.files.to_list()[0].dirname

    build_output = ctx.attr.data.files.to_list()[0].path
    ctx.actions.run(
        inputs = files,
        outputs = [output_file],
        executable = ctx.attr.interpreter.files.to_list()[0],
        arguments = ["-m", "awscli", "s3", "sync", build_output, bucket_path],
        env = env,
        tools = [x.files for x in ctx.attr.aws_with_deps],
    )

    return DefaultInfo(files = depset([output_file]))

upload_cdn = rule(
    implementation = _upload_cdn_impl,
    attrs = _ATTRS,
)
