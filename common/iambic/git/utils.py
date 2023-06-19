import hashlib
import time
from typing import Optional

import httpx
import jwt
from sqlalchemy.dialects.postgresql import ENUM

from common.config import config, models
from common.config.globals import GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY
from common.lib.redis import RedisHandler
from common.models import IambicRepoDetails
from common.tenants.models import Tenant  # noqa: F401

log = config.get_logger(__name__)

RequestStatus = ENUM(
    "Pending",
    "Approved",
    "Rejected",
    "Expired",
    "Running",
    "Failed",
    name="RequestStatusEnum",
)

IAMBIC_REPOS_BASE_KEY = "iambic_repos"


def list_tenant_repo_details(tenant_name: str) -> list[IambicRepoDetails]:
    return (
        models.ModelAdapter(IambicRepoDetails)
        .load_config(IAMBIC_REPOS_BASE_KEY, tenant_name)
        .models
    )


async def get_repo_access_token(
    tenant: Tenant,
    git_provider: Optional[str] = None,
    repo_details: Optional[IambicRepoDetails] = None,
    installation_id: Optional[str] = None,
    default: Optional[str] = None,
) -> str:
    """Generates an access token to make API requests to the given repo

    Args:
        tenant (Tenant): The tenant to generate the token for
        git_provider (Optional[str]): The git provider to generate the token for. Defaults to None.
        repo_details (Optional[IambicRepoDetails]): The repo details to generate the token for. Defaults to None.
        installation_id (Optional[str]): The installation id to generate the token for. Defaults to None.
        default (Optional[str]): The default token to return if no token can be generated. Defaults to None.
    return:
        str: The access token
    """
    assert bool(git_provider) ^ bool(
        repo_details
    ), "Must provide either git_provider or repo_details"
    if not git_provider:
        git_provider = repo_details.git_provider

    if git_provider != "github":
        return default
    elif git_provider == "github" and not installation_id:
        raise AssertionError("Github App is not connected")

    repo_name = None
    git_domain = "github.com"
    if repo_details:
        repo_name = repo_details.repo_name
        git_domain = repo_details.git_domain

    if repo_name:
        # Can only cache the token if we have a repo name to help build the redis key
        # Attempt get from cache
        # Use md5 so key isn't useful on its own and is a fixed length w/ no special chars
        red = await RedisHandler().redis(tenant.name)
        hashed_repo_name = hashlib.md5(repo_name.encode()).hexdigest()
        cache_key = f"{tenant.name}:iambic_repo:{hashed_repo_name}:access_token"
        if access_token := red.get(cache_key):
            return access_token

    # Generate the JWT
    now = int(time.time())
    payload = {
        "iat": now,  # Issued at time
        "exp": now + (10 * 60),  # JWT expiration time (10 minute maximum)
        "iss": GITHUB_APP_ID,  # GitHub App's identifier
    }
    jwt_token = jwt.encode(payload, GITHUB_APP_PRIVATE_KEY, algorithm="RS256")

    # Use the JWT to authenticate as the GitHub App
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github.machine-man-preview+json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.{git_domain}/app/installations/{installation_id}/access_tokens",
            headers=headers,
        )
    response.raise_for_status()
    access_token = response.json()["token"]
    if repo_name:
        # Set cache
        red.set(cache_key, access_token, ex=60 * 45)  # TTL is 45 minutes

    return access_token


async def list_github_repos(
    access_token: Optional[str] = None,
    tenant: Optional[Tenant] = None,
    git_provider: Optional[str] = None,
    repo_details: Optional[IambicRepoDetails] = None,
    installation_id: Optional[str] = None,
    default: str = None,
) -> list[dict]:
    """Return a list of repo definition dicts for the given tenant

    Accepts either an access_token or (tenant and git_provider)

    Args:
        access_token (Optional[str]): The access token to use to make the request. Defaults to None.
        tenant (Optional[Tenant]): The tenant to get the repos for. Defaults to None.
        git_provider (Optional[str]): The git provider to get the repos for. Defaults to None.
        repo_details (Optional[IambicRepoDetails]): The repo details to get the repos for. Defaults to None.
        installation_id (Optional[str]): The installation id to get the repos for. Defaults to None.
        default (str): The default value to return if no repos can be found. Defaults to None.
    return:
        list[dict]: The list of repo definition dicts
    """
    # maximum supported value is 100
    # GitHub default is 30
    # To test, change this to 1 to test pagination stitching response
    # why 100? with gzip compression, it's better to have
    # more results in single response, and let's compression take advantage
    # of repeated strings.
    assert bool(access_token) ^ bool(
        tenant and git_provider
    ), "Must provide either access_token or tenant and git_provider"
    if not access_token:
        access_token = await get_repo_access_token(
            tenant=tenant,
            git_provider=git_provider,
            repo_details=repo_details,
            installation_id=installation_id,
            default=default,
        )

    per_page = 100
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
        "Accept-Encoding": "gzip, deflate, br",
        "per_page": f"{per_page}",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/installation/repositories", headers=headers
        )
        response.raise_for_status()
        repos = response.json()
        # handle pagination: https://docs.github.com/en/rest/guides/using-pagination-in-the-rest-api?apiVersion=2022-11-28
        while "next" in response.links:
            response = await client.get(response.links["next"]["url"], headers=headers)
            response.raise_for_status()
            repos["repositories"].extend(response.json()["repositories"])
    return repos.get("repositories", [])
