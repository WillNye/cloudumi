from subprocess import run

if __name__ == "__main__":
    version = "1.5.303"
    branch_name = "task.en-1057-serve-frontend-cf-cdn"
    bucket_path = "s3://noq-global-frontend/1.5.303/task.en-1057-serve-frontend-cf-cdn/"
    public_url = "https://d2mxcvfujf7a5q.cloudfront.net/1.5.303/task.en-1057-serve-frontend-cf-cdn/"
    repo_dir = "/home/matt/dev/noq/cloudumi"

    output = []
    output.append(
        run("yarn", capture_output=True, cwd=repo_dir + "/frontend").stdout.decode()
    )
    output.append(
        run(
            "yarn --cwd frontend build_template".split(" "),
            capture_output=True,
            cwd=repo_dir,
        ).stdout.decode()
    )
    output.append(
        run(
            f"aws s3 sync frontend/dist/ {bucket_path}".split(" "),
            capture_output=True,
            cwd=repo_dir,
        ).stdout.decode()
    )
    for out in output:
        print(f"Stdout: {out}\n")
