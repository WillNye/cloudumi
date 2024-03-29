# CloudUmi

Disclaimer: This code is provided as-is. The instructions are unclear and all-over the place. Good luck, and God Speed.

> Quick Start

- DevOps
  - [Deploy with Terraform and Bazel](deploy/README.md)
  - [Build with Bazel](#build-instructions)
- API:
  - [Overview](api/README.md)
- Backend:
  - [Celery Tasks](common/celery_tasks/README.md)
- Frontend:
  - [Overview](frontend/README.md)
- Docs:
  - [Overview](docs/README.md)
- How to Build:
  - [Build Instructions](#build-instructions)
- Testing:
  - [Testing Instructions](util/tests/README.md)
- Debugging and Troubleshooting:
  - [Debug/Troubleshoot](docs/debug_troubleshooting/README.md)

# Build Instructions

Cloudumi is a mono repo to build all of the distinct services. To get started, follow the Quick Start instructions below.

Each target has a name that uniquely identifies a build target. The path disambiguates build targets within different projects / folders.

## Pre-requisites

- Install ecs-cli: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI_installation.html
- Install docker: https://docs.docker.com/get-docker/
- Install docker-compose: https://docs.docker.com/compose/install/
- Optionally install pyenv: https://github.com/pyenv/pyenv#basic-github-checkout
- Install python 3.11.x & dependencies (requirements.lock)
- Install tfsec: https://github.com/aquasecurity/tfsec#installation

## Quick Start

- Ensure you have a python environment with version 3.11+
- Use the most advanced and doubtlessly the most superior IDE available to you: VSCODE. We have created deployment profiles, which are contained in the git repo. You may access them here by clicking the icon on the left pane with the play button and the bug on it and then the drop down towards the top of your IDE.
- All dependencies are stored in `requirements.lock` in the root of the mono repo

# Setup your dev environment

- Python 3.11, recommend using pyenv, create a venv and `pip install -r requirements.lock`
- Optionally install fluent-bit to run SaaS with fluent-bit running: `curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | sh`
- OR: https://docs.fluentbit.io/manual/installation/getting-started-with-fluent-bit
- Note: if you don't have a `fluent-bit` binary running on your system, the binary build jobs (`//api:bin, //common/celery_tasks:bin` will still run and provide a warning that fluent-bit cannot be found) - this will not impact our staging or prod deployments.

## Local environment

- Visual Studio Code (and pretty much any other IDE): we ship .vscode config files for VSC specifically to run targets. For other IDEs, ensure that your PYTHONPATH is set to the root of the mono repo; this "should" just work. For VSCODE, just make sure you have the bazel plugin (and relevant plugin for your choice of IDE: https://marketplace.visualstudio.com/items?itemName=BazelBuild.vscode-bazel)
- For command line development: set your PYTHONPATH to the root of the monorepo - `PYTHONPATH=~/dev/noq/cloudumi python ...`
- Use `docker-compose` or `docker compose` to run the docker compose files to setup a development environment: `docker-compose -f deploy/docker-compose-dependencies.yaml up -d`

## Local environment run

- Make sure you've [setup your environment](https://perimy.atlassian.net/wiki/spaces/MAIN/pages/41648129/Development+Environment+Setup)
- Navigate to https://cloudumidev.com

## Managing Python Dependencies

This project uses `pip-tools` to manage the Python dependencies. `pip-tools` allows us to specify our high-level requirements, and it then takes care of figuring out which specific versions of each package we should use in order to keep everything compatible. This can greatly simplify the process of adding, updating, or removing dependencies.

We have a few helpful `make` commands for managing the `pip-tools` dependencies, all of which are included in our `Makefile`.

### Updating Requirements

**Command: `make python_requirements_update`**

When adding a new package to the project, specify the package in the appropriate `requirements.in` or `requirements-test.in` file, then run this command. It will update the `requirements.lock` file based on all the `requirements.in` and `requirements-test.in` files present in the project. This is necessary to ensure the new package and its dependencies are locked to specific, compatible versions.

### Upgrading All Packages

**Command: `make python_requirements_upgrade_all`**

To upgrade all Python packages to their latest supported versions, use this command. This will update all packages listed in the `requirements.lock` file. It's a good idea to do this periodically to keep up to date with the latest features and security fixes. However, be sure to thoroughly test your project after running this command, as major version upgrades may include breaking changes.

### Upgrading a Specific Package

**Command: `make python_requirements_upgrade_package PACKAGE_NAME=<PACKAGE_NAME>`**

To upgrade a specific Python package to its latest version, use this command. Replace `<PACKAGE_NAME>` with the name of the package you wish to upgrade. This command will only upgrade the specified package and its dependencies, leaving all other packages untouched. Use this command if a specific package has a new feature or fix you need, and you don't want to upgrade all packages at this time.

For example, to upgrade the `structlog` package, you would run: `make python_requirements_upgrade_package PACKAGE_NAME=structlog`

Please refer to the `pip-tools` [documentation](https://github.com/jazzband/pip-tools) for more detailed information about managing Python dependencies with `pip-tools`.

## Profiling

To profile a function all you have to do is `pip install pyinstrument` and drop in this snippet.

```python
import pyinstrument

p = pyinstrument.Profiler()
p.start()
# function or code snippet to profile
p.stop()
p.print(show_all=True)
```

## Finding raw config

Configs are stored in dynamo which you can access at `localhost:8001`
The table containing raw configs is `dev_cloudumi_tenant_static_configs`
Within the UI you can perform all CRUD operations on your configs

### OR:

- Just run the services:
- `docker-compose -f deploy/docker-compose-dependencies.yaml up -d`

## Testing

- Either use the most superior IDE known to people, named PyCharm or run `make test`, if using the IDE there is a settings.json file in the test README that can be used to get setup.

# Versioning

We use GitVersion to automatically version our mono repo by providing modifier nouns in the commit message header: +semver: major, +semver: minor, +semver: patch.

# Troubleshooting

- In the event that docker containers fail to run with an error on a symbol not found \*.so exception, use the `how to run in sysbox` instructions to run a fully isolated Ubuntu-based build environment that allows docker in docker on 20.04.

## Tracing on locahost

We support Zipkin tracing when debugging locally. To enable tracing, update `configs/development_account/saas_development.yaml`
and uncomment the `tracing` section:

```yaml
tracing:
  enabled: true
```

Then run Zipkin: `docker run -d -p 9411:9411 openzipkin/zipkin`

Start the API, browse to Noq, then view traces at http://localhost:9411/

## Using ecsgo for Staging and Production Environments

[ecsgo](https://github.com/tedsmitt/ecsgo) is a utility that allows you to quickly switch between and connect to Amazon ECS clusters. To use `ecsgo` with your staging and production environments, follow these steps:

### Prerequisites

1. Make sure you have the [AWS CLI](https://aws.amazon.com/cli/) installed and configured with the appropriate credentials for the `staging/staging_admin` or `prod/prod_admin` profiles.

2. Install `ecsgo` by following the instructions in its [GitHub repository](https://github.com/tedsmitt/ecsgo).

### Using ecsgo with Makefile Commands

1. Clone your project repository and navigate to the project directory.

2. Run one of the following `make` commands to use `ecsgo` with the desired environment:

   - Staging environment:

     ```bash
     make ecsgo-staging
     ```

   - Production environment:

     ```bash
     make ecsgo-prod
     ```

### Update your local database

We use Alembic to handle Database migrations. When developing, and working across multiple branches,
sometimes it is just easier to delete your database and start over again with a fresh database.
Also during development, we try to condense all alembic migrations into one single migration file
per branch.

Here are the steps to follow to update your local database:

1. docker-compose -f deploy/docker-compose-dependencies.yaml down
2. docker volume rm deploy_cloudumi-pg

# Note: For Kayizzi, this didn't work for removing his database, you may want to manually delete the `noq` database using DBeaver or PG Admin

# PG Admin runs on localhost:8008 through the Docker-Compose file.

3. docker-compose -f deploy/docker-compose-dependencies.yaml up -d
4. (In VSCode) Alembic Upgrade Head
5. (In VSCode) Update Local Config and Populate Redis

## Connecting to Celery Flower

Celery Flower contains a web interface that details Celery task status.
To connect to the web interface, install [ecs-tunnel](https://github.com/alastairmccormack/ecs-tunnel) and follow
the steps below:

### Prerequisites

1. Make sure you have the [AWS CLI](https://aws.amazon.com/cli/) installed and configured with the appropriate credentials for the `staging/staging_admin` or `prod/prod_admin` profiles.

2. Install the `ecs-tunnel` utility using `pip`:

   ```bash
   pip3 install ecs-tunnel
   ```

   For more details about `ecs-tunnel`, visit its [PyPI page](https://pypi.org/project/ecs-tunnel/).

### Connecting to the Celery Flower Web Interface

1. Run the following `make` command to create a tunnel from your local machine to the Celery Flower service in the staging or production environment:

   - Staging environment:

     ```bash
     make ecs-tunnel-staging-celery-flower
     ```

   - Production environment:

     ```bash
     make ecs-tunnel-prod-celery-flower
     ```

2. Open your web browser and navigate to `http://localhost:7101` to access the Celery Flower web interface.

## Setting up ecs-tunnel and Connecting to the Fargate Task

The `ecs-tunnel` utility is used to create a tunnel between your local machine and a specific Fargate task in the staging environment. To set up `ecs-tunnel` and use the provided `Makefile` command, follow these steps:

### Prerequisites

1. Make sure you have the [AWS CLI](https://aws.amazon.com/cli/) installed and configured with the appropriate credentials for the `staging/staging_admin` profile.

2. Install the `ecs-tunnel` utility using `pip`:

   ```
   pip3 install ecs-tunnel
   ```

   For more details about `ecs-tunnel`, visit its [PyPI page](https://pypi.org/project/ecs-tunnel/).

Here is the updated README snippet with instructions to run `make ecs-tunnel-staging-ssh` and the SSH command and password to connect:

### Connecting to the Fargate Task

1. Run the following `make` command to set the SSH password and create an SSH tunnel from your local machine to the Fargate task:

   ```bash
   make ecs-tunnel-staging-ssh
   ```

2. The command will output the SSH connection details. Use the provided SSH command and password to connect to the Fargate task:

   ```bash
   ssh root@127.0.0.1 -p 2222
   ```

   Password: TEMP_PASS

### Connecting to Postgres DB in a cluster (TODO)

(The below doesn't work verbatim yet.. Not sure why)

To connect to a PostgreSQL database that is accessible by an ECS container but not directly by the user, you can use the same ecs-tunnel utility above to create an SSM tunnel from your local machine to the ECS container running the PostgreSQL server. Here are the general steps to follow:

AWS_PROFILE=<aws_profile_name> ecs-tunnel -L <local_port>:<postgres_host>:<postgres_port> -c <ecs_cluster_name> -t <ecs_task_id> --region <aws_region>

For example, to connect to the staging database, you can run the following command:

```bash
AWS_PROFILE=prod/prod_admin ecs-tunnel -L 55432:noq-dev-shared-prod-1.cluster-cxpteqvues57.us-west-2.rds.amazonaws.com:5432 -c noq-dev-shared-prod-1 -t 7d987a7f02064b389b4385142a82c026 --region us-west-2
```

## Create a new Tenant

Go to Postman, and login as engineering@noq.dev

- In your CLI, generate a registratin code for the user

  ```bash
  # Substitute email below with the e-mail of the registrant
  python -c 'import hashlib ; email="curtis@noq.dev"; print(hashlib.sha256(f"noq_tenant_{email}".encode()).hexdigest()[0:20])'
  ```

- Find the `Tenant Registration Request` Request
- Change the appropriate parameters, including registration_code
- Select the `Prod Tenant Registration (Shared)` Environment
- Submit your request

## Slack bot

The Slack app requires a static publicly accessible URL with a valid SSL certificate. localtunnel is a good option to configure this. ngrok is another one but it can get annoying when the domain changes every time you restart the tunnel. Setting up an actual domain with an actual certificate works well. In this example, we will set up a certificate for parlicy.com:

```bash
sudo certbot certonly -d "*.parlicy.com" --manual --preferred-challenges=dns
```

Then configure the DNS TXT records on your domain provider.

Once the certificate is generated, run the frontend with the following configuration:

SSL_CRT_FILE=/etc/letsencrypt/live/parlicy.com/cert.pem
SSL_KEY_FILE=/etc/letsencrypt/live/parlicy.com/privkey.pem
NODE_EXTRA_CA_CERTS=/etc/letsencrypt/live/parlicy.com/chain.pem

## Debugging traffic hitting the web service

If you need to debug the traffic hitting the web service, you can use tcpdump to capture the packets on port 8092. Tcpdump is a command-line packet analyzer that allows you to intercept and display network traffic in real-time.

To capture traffic hitting the web service, you can use the following command:

```bash
sudo tcpdump -i any -A -s0 'tcp port 8092'
```

This command captures all TCP traffic on port 8092, and displays the packet payload in ASCII format using the "-A" option. The "-s0" option sets the snaplength to zero, which means the full packet payload will be captured.

After connecting to the API service with `ecsgo`, run this command on the terminal to see the traffic hitting the web service. You will likely need to install
tcpdump on the container first with `sudo apt-get install tcpdump`.

## Testing the old UI (UI V1)

The new UI is built by `vite` and deployed to our Staging and Production environments during
our normal deployment process. The [Cookie-Editor](https://cookie-editor.cgagnier.ca/) extension for Chrome can be used to create a cookie, which can then be used to test the new UI.

1. Visit [https://corp.staging.noq.dev](https://corp.staging.noq.dev), [https://corp.noq.dev](https://corp.noq.dev) (Or any tenant for that matter)
2. Use `Cookie-Editor` to add a cookie with a key of `V1_UI` and any value
3. Refresh the page
   ==> Voila! The new UI should load.

## Testing Changes in Staging

The staging API container uses [watchdog](https://pypi.org/project/watchdog/) and watchmedo to automatically restart the API server whenever any Python files under /app/api are modified. This allows for faster development and testing of changes in the staging environment.

Triggering a Restart
If you're making changes that don't involve Python files under /app/api, you can still trigger a restart by adding an empty comment (#) at the top of /app/api/**main**.py. This will be treated as a modification and cause the API server to restart.

Verifying Restart in CloudWatch Logs
To confirm that the container has restarted, you can check the log events in Amazon CloudWatch Logs. Follow these steps:

Sign in to the AWS Management Console and open the CloudWatch console.
In the navigation pane, choose Logs > Log groups.
Locate and select the log group for your staging API container (usually named as {{ ecs_cluster_name }}).
Choose the appropriate log stream (typically prefixed with "web" if you followed the awslogs-stream-prefix configuration in your task definition).
Look for log events indicating the restart of the API server. You can also use CloudWatch Logs Insights to query and analyze the logs for specific patterns or events related to the restart.
By using watchdog and watchmedo in the staging environment, you can quickly test and iterate on changes without having to manually restart the API server or rebuild the entire container.

## Updating AWS Service Definitions in the Frontend

If you need to update the AWS service definitions that are specified in the frontend, it's a simple process that involves running a make command. This command runs a Python script which pulls the latest service definitions from policyuniverse and updates the relevant JSON file in your frontend assets.

```bash
make update_aws_service_definitions_frontend
```

## Serverless Functions

This repository contains code for serverless functions that are deployed with the [Serverless Framework](https://www.serverless.com/). One of these functions is the `ExceptionReporting` serverless function. It's a simple function that receives HTTP POST requests and copies the data from the requests to an S3 bucket, and sends a message to an SQS queue with the file it created. serverless makes the deployment process much easier than it would be to define everything in Terraform, and gives us a framework for possibly adding more such functions in the future.

You will need a .env file in the same directory as serverless.yml `deploy/serverless` with the following variables:

SENDGRID_PASSWORD="..."
SENDGRID_FROM_EMAIL=notifications@noq.dev
SENDGRID_USERNAME=apikey

There's another function that is used to send hourly email digests when there are messages in the sqs queue (see `serverless.yml` for details).

### ExceptionReporting function

#### Functionality

The `ExceptionReporting` function, when triggered, performs the following actions:

- It receives HTTP POST requests at the `/report_exception` endpoint.
- The function puts this data into an S3 bucket specified in an environment variable which is defined in deploy/serverless/serverless.yml.

#### Deployment

The function can be deployed in two environments: `dev` and `prod`. The configuration for each environment is defined in `serverless.yml` file.

Below are the instructions for how to deploy the serverless function:

##### Prerequisites

- Install Serverless framework if you haven't done it yet. You can use the following command:

```
npm install -g serverless
```

##### Deploy to `dev`:

1. Execute the following command: `make serverless-deploy-dev` or `make serverless-deploy-prod` from the base cloudumi directory. This will deploy the serverless function to the production account for the specified stage.
1. After the deployment, a curl command will be printed on the console. Use this to validate the function.

#### Editing the Function

If you want to change the behavior of the function or add new features, you can edit the appropriate files under the `deploy/serverless` directory.
