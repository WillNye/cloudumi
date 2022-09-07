CDN_BUCKET_PREFIX = "s3://noq-global-frontend/"
CDN_PUBLIC_URL = "https://d2mxcvfujf7a5q.cloudfront.net/"

def _version_impl(ctx):
    src = ctx.files.srcs[0]
    version_out = ctx.actions.declare_file("version")
    branch_out = ctx.actions.declare_file("branch")
    bucket_path_out = ctx.actions.declare_file("bucket_path")
    public_url_out = ctx.actions.declare_file("public_url")

    ctx.actions.run_shell(
        inputs = ctx.files.srcs,
        outputs = [version_out, branch_out, bucket_path_out, public_url_out],
        command = """
          full_path="$(readlink -f -- "{src_full}")"
          # Trim the src.short_path suffix from full_path. Double braces to
          # output literal brace for shell.
          cd ${{full_path%/{src_short}}};
          git describe --tags --abbrev=0 >> {version_out};
          git rev-parse --short HEAD >> {branch_out};
          echo "{cdn_bucket_prefix}{version_out}" >> {bucket_path_out};
          echo "{cdn_public_url}{version_out}/{branch_out}" >> {public_url_out}
        """.format(src_full = src.path, src_short = src.short_path, cdn_bucket_prefix = CDN_BUCKET_PREFIX,
                   cdn_public_url = CDN_PUBLIC_URL, version_out = version_out.path, branch_out = branch_out.path,
                   bucket_path_out = bucket_path_out.path, public_url_out = public_url_out.path),
        execution_requirements = {
            "no-sandbox": "1",
            "no-remote": "1",
            "local": "1",
        },
    )

version = rule(
    implementation = _version_impl,
    attrs = {
        "srcs": attr.label_list(
            allow_files = ["BUILD"],
            doc = "",
        ),
    }
)
