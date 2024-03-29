from subprocess import run

if __name__ == "__main__":
    version = "1.5.308"
    branch_name = "main"
    bucket_path = "s3://noq-global-frontend/1.5.308/main/"
    public_url = "https://d2mxcvfujf7a5q.cloudfront.net/1.5.308/main/"
    repo_dir = "/home/ccastrapel/localrepos/cloudumi"

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
