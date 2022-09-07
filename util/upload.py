import pathlib
import sys
from subprocess import run

if __name__ == "__main__":
    try:
        repo_dir = sys.argv[1]
    except IndexError:
        print("Usage: upload.py REPO_DIR")
        sys.exit(1)
    version = open("version").read()
    branch = open("branch").read()
    bucket_path = open("bucket_path").read()
    public_url = open("public_url").read()

    repo_path = pathlib.Path(repo_dir)
    if not repo_path.exists():
        print(f"Repo directory {repo_dir} does not exist")
        sys.exit(1)
    version = (
        run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=repo_dir,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    print(f"Version: {version}")
    branch_name = (
        run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
        )
        .stdout.decode()
        .replace("/", ".")
        .strip()
    )
    print(f"Branch Name: {branch_name}")
    bucket_path = f"s3://noq-global-frontend/{version}/{branch_name}/"
    print(f"Bucket Path: {bucket_path}")
    public_url = f"https://d2mxcvfujf7a5q.cloudfront.net/{version}/{branch_name}/"
    print(f"Public URL: {public_url}")

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
