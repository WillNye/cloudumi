import json
import time

from common.config import config
from common.lib.change_request import generate_policy_name
from common.lib.plugins import get_plugin_by_name
from common.lib.scm.git import Repository
from common.lib.scm.git.bitbucket import BitBucket
from common.models import (
    ChangeModelArray,
    ExtendedRequestModel,
    GenericFileChangeModel,
    RequestCreationModel,
    RequestStatus,
    UserModel,
)

log = config.get_logger()


# TODO:
# Generate PR in GitHub for a demo
# Generate cross-account resource policy in Terraform
# Show cross-Terraform/Cloud Native policy generation
# Show sts assume role
# Generate list of resources for frontend, allow filtering
# Interpret json from SVG canvas to generate policy
# How can this be generalized more?
# Think about repokid removing permissions in the future
# How should we genericize resources whether they are defined in TF, CF, or cloud native?
# Can we parse Terraform modules to get all of the arguments for a given resource type?
# Most important thing: Build a powerful API
# Generic canvas editor to call or web apis to do stuff. Must not let it talk to internal
# APIs


async def generate_terraform_request_from_change_model_array(
    request_creation: RequestCreationModel,
    user: str,
    extended_request_uuid: str,
    host: str,
) -> ExtendedRequestModel:
    repositories_for_request = {}
    primary_principal = None
    t = int(time.time())
    generated_branch_name = f"{user}-{t}"
    policy_name = await generate_policy_name(None, user, host)
    repo_config = None

    auth = get_plugin_by_name(
        config.get_host_specific_key("plugins.auth", host, "cmsaas_auth")
    )()
    # Checkout Git Repo and generate a branch name for the user's change
    for change in request_creation.changes.changes:
        if primary_principal and change.principal != primary_principal:
            raise Exception("Changes must all affect the same principal")
        primary_principal = change.principal
        discovered_repository_for_change = False
        if repositories_for_request.get(change.principal.repository_name):
            continue
        # Find repo
        for r in config.get_host_specific_key(
            "cache_resource_templates.repositories", host, []
        ):
            if r["name"] == change.principal.repository_name:
                repo_config = r
                repo = Repository(
                    r["repo_url"], r["name"], r["authentication_settings"]["email"]
                )
                await repo.clone(depth=1)
                git_client = repo.git
                git_client.reset()
                git_client.checkout(b=generated_branch_name)
                repositories_for_request[change.principal.repository_name] = {
                    "main_branch_name": r.get("main_branch_name", "master"),
                    "repo": repo,
                    "git_client": git_client,
                    "config": r,
                }
                discovered_repository_for_change = True
                break
        if not discovered_repository_for_change:
            raise Exception("No matching repository found for change in configuration")
    request_changes = ChangeModelArray(changes=[])
    for change in request_creation.changes.changes:
        git_client = repositories_for_request[change.principal.repository_name][
            "git_client"
        ]

        formatted_policy_doc = json.dumps(change.policy.policy_document, indent=2)
        repo = repositories_for_request[change.principal.repository_name]["repo"].repo
        main_branch_name = repositories_for_request[change.principal.repository_name][
            "main_branch_name"
        ]
        git_client.checkout(f"origin/{main_branch_name}", change.principal.file_path)
        change_file_path = f"{repo.working_dir}/{change.principal.file_path}"
        with open(change_file_path, "r") as f:
            original_text = f.read()
        terraform_formatted_policy_string = f"""<<-EOT
{formatted_policy_doc}
EOT"""
        terraform_formatted_policy = """\nresource "aws_iam_role_policy" "{policy_name}" {{
  name = {policy_name}
  role = {role_tf_identifier}.id

  policy = {policy}
}}
        """.format(
            role_tf_identifier=change.principal.resource_identifier,
            policy=terraform_formatted_policy_string,
            policy_name=policy_name,
        )
        updated_text = original_text + terraform_formatted_policy
        with open(change_file_path, "w") as f:
            f.write(updated_text)

        request_changes.changes.append(
            GenericFileChangeModel(
                principal=primary_principal,
                action="attach",
                change_type="generic_file",
                policy=updated_text,
                old_policy=original_text,
                encoding="hcl",
            )
        )
        git_client.add(change_file_path)
        git_client.commit(m=f"Added {policy_name} to {change.principal.file_path}")
    pull_request_url = ""
    if not request_creation.dry_run:
        commit_title = f"Generated PR for {user}"
        commit_message = (
            f"This request was made through Self Service\n\nUser: {user}\n\n"
            f"Justification: {request_creation.justification}"
        )

        git_client.commit(m=commit_message)
        git_client.push(u=["origin", generated_branch_name])
        if repo_config["code_repository_provider"] == "github":
            pass
        if repo_config["code_repository_provider"] == "bitbucket":
            bitbucket = BitBucket(
                repo_config["code_repository_config"]["url"],
                config.get_host_specific_key(
                    "{key}".format(
                        key=repo_config["code_repository_config"][
                            "username_config_key"
                        ],
                    ),
                    host,
                ),
                config.get_host_specific_key(
                    repo_config["code_repository_config"]["password_config_key"],
                    host,
                ),
            )
            pull_request_url = await bitbucket.create_pull_request(
                repo_config["project_key"],
                repo_config["name"],
                repo_config["project_key"],
                repo_config["name"],
                generated_branch_name,
                repo_config["main_branch_name"],
                commit_title,
                commit_message,
            )
        else:
            raise Exception(
                f"Unsupported `code_repository_provider` specified in configuration: {repo_config}"
            )

    for repo_name, repo_details in repositories_for_request.items():
        await repo_details["repo"].cleanup()

    if not pull_request_url and not request_creation.dry_run:
        raise Exception("Unable to generate pull request URL")

    return ExtendedRequestModel(
        id=extended_request_uuid,
        request_url=pull_request_url,
        principal=primary_principal,
        timestamp=int(time.time()),
        requester_email=user,
        approvers=[],
        request_status=RequestStatus.pending,
        changes=request_changes,
        requester_info=UserModel(
            email=user,
            extended_info=await auth.get_user_info(user, host),
            details_url=config.get_employee_info_url(user, host),
            photo_url=config.get_employee_photo_url(user, host),
        ),
        comments=[],
        cross_account=False,
    )
