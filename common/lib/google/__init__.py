import asyncio
import html
import sys
from typing import Any, Dict, List, Optional, Union

import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from retrying import retry
from validate_email import validate_email

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import (
    BackgroundCheckNotPassedException,
    BulkAddPrevented,
    DifferentUserGroupDomainException,
    MissingConfigurationValue,
    NoCredentialSubjectException,
    NoGroupsException,
    NotAMemberException,
    UnableToModifyRestrictedGroupMembers,
    UnauthorizedToAccess,
    UserAlreadyAMemberOfGroupException,
)
from common.lib.asyncio import aio_wrapper
from common.lib.auth import can_modify_members
from common.lib.dynamo import UserDynamoHandler
from common.lib.groups import does_group_require_bg_check
from common.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent_bit"))()

log = config.get_logger()
auth = get_plugin_by_name(config.get("_global_.plugins.auth", "cmsaas_auth"))()


async def add_user_to_group_task(
    tenant: str,
    member: str,
    group: str,
    requesting_user: str,
    requesting_users_groups: List[str],
    semaphore=None,
    service: None = None,
) -> Dict[str, Union[str, bool]]:
    if not semaphore:
        semaphore = asyncio.BoundedSemaphore(10)
    async with semaphore:
        stats.count(
            "add_user_to_group_task.attempt",
            tags={
                "member": member,
                "group": group,
                "requesting_user": requesting_user,
                "tenant": tenant,
            },
        )
        member = member.strip()
        result = {
            "Action": "Add user",
            "Member": member,
            "Group": group,
            "Error": False,
        }
        log_data = {
            "function": f"{__name__, sys._getframe().f_code.co_name}",
            "action": "Add user",
            "tenant": tenant,
            "member": member,
            "group": group,
        }
        try:
            group_info = await auth.get_group_info(tenant, group, members=False)
            can_add_remove_members = can_modify_members(
                tenant, requesting_user, requesting_users_groups, group_info
            )

            if not can_add_remove_members:
                result[
                    "Result"
                ] = "You are unable to add members to this group. Maybe it is restricted."
                result["Error"] = True
                error = f"There was at least one problem. {result['Result']}"
                log_data["error"] = error
                log.warning(log_data, exc_info=True)

                return result
            if not validate_email(member):
                result["Result"] = "Invalid e-mail address entered"
                result["Error"] = True
                log_data["message"] = "Error"
                log_data["error"] = result["Result"]
                log.warning(log_data, exc_info=True)
                return result

            if (
                not group_info.allow_third_party_users
                and not await auth.does_user_exist(tenant, member)
            ):
                result[
                    "Result"
                ] = "User does not exist in our environment and this group doesn't allow third party users."
                result["Error"] = True
                log_data["message"] = "Error"
                log_data["error"] = result["Result"]
                log.warning(log_data, exc_info=True)
                return result

            await add_user_to_group(
                tenant, member, group, requesting_user, service=service
            )
            result["Result"] = "Successfully added user to group"
            return result
        except Exception as e:
            result["Result"] = html.escape(str(e))
            result["Error"] = True
            error = f"There was at least one problem. {e}"
            log_data["message"] = "Error"
            log_data["error"] = error
            log.error(log_data, exc_info=True)
            return result


async def remove_user_from_group_task(
    tenant: str,
    member: str,
    group: str,
    requesting_user: str,
    requesting_users_groups: List[str],
    semaphore=None,
    service: None = None,
) -> Dict[str, Union[str, bool]]:
    if not semaphore:
        semaphore = asyncio.BoundedSemaphore(10)
    async with semaphore:
        stats.count(
            "remove_user_from_group_task.attempt",
            tags={
                "member": member,
                "group": group,
                "requesting_user": requesting_user,
                "tenant": tenant,
            },
        )
        member = member.strip()
        result = {
            "Action": "Remove user",
            "Member": member,
            "Requesting User": requesting_user,
            "Group": group,
            "Error": False,
        }
        log_data = {
            "function": f"{__name__, sys._getframe().f_code.co_name}",
            "action": "Remove user",
            "member": member,
            "group": group,
            "tenant": tenant,
        }

        try:
            group_info = await auth.get_group_info(tenant, group, members=False)
            can_add_remove_members = can_modify_members(
                tenant, requesting_user, requesting_users_groups, group_info
            )

            if not can_add_remove_members:
                result[
                    "Result"
                ] = "You are unable to remove members from this group. Maybe it is restricted."
                result["Error"] = True
                error = f"There was at least one problem. {result['Result']}"
                log_data["error"] = error
                log.warning(log_data, exc_info=True)

                return result

            if not validate_email(member):
                result[
                    "Result"
                ] = "Invalid e-mail address entered, or user doesn't exist"
                result["Error"] = True
                log_data["message"] = "Error"
                log_data["error"] = result["Result"]
                log.warning(log_data, exc_info=True)
                return result

            await remove_user_from_group(
                tenant, member, group, requesting_user, service=service
            )
            result["Result"] = "Successfully removed user from group"
            return result
        except Exception as e:
            result["Result"] = str(e)
            result["Error"] = True
            error = f"There was at least one problem. {e}"
            log_data["message"] = "Error"
            log_data["error"] = error
            log.error(log_data, exc_info=True)
            return result


async def get_service(
    tenant: str, service_name: str, service_path: str, group: str
) -> Resource:
    """
    Get a service connection to Google. You'll need to generate a GCP service account first from instructions here:
    https://hawkins.gitbook.io/consoleme/configuration/authentication-and-authorization/google-groups-support

    Noq requires that you either have a service key file with content like below,
    and you've set the configuration for `google.service_key_file` to the full path of that file on disk,
    or you've just put the json for this in your Noq configuration in the `secrets.google.service_key_dict` configuration
    key.

    There are sensitive secrets here, so if you want to
    reference them directly in configuration, we encourage you to store these secrets in AWS Secrets Manager
    https://hawkins.gitbook.io/consoleme/configuration/aws-secret-manager-integration
        {
          "type": "service_account",
          "project_id": "cons...",
          "private_key_id": "dc61.....",
          "private_key": "-----BEGIN PRIVATE KEY-----\nMII.....",
          "client_email": "cons...@cons....gserviceaccount.com",
          "client_id": "1234....",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://oauth2.googleapis.com/token",
          "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
          "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/consolem...."
        }

    """

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "service_name": service_name,
        "service_path": service_path,
        "tenant": tenant,
        "group": group,
        "message": f"Building service connection for {service_name} / {service_path}",
    }
    log.debug(log_data)
    if config.get_tenant_specific_key("google.service_key_file", tenant):
        admin_credentials = service_account.Credentials.from_service_account_file(
            config.get_tenant_specific_key("google.service_key_file", tenant),
            scopes=config.get_tenant_specific_key(
                "google.admin_scopes",
                tenant,
                ["https://www.googleapis.com/auth/admin.directory.group"],
            ),
        )
    elif config.get_tenant_specific_key("secrets.google.service_key_dict", tenant):
        admin_credentials = service_account.Credentials.from_service_account_info(
            config.get_tenant_specific_key("secrets.google.service_key_dict", tenant),
            scopes=config.get_tenant_specific_key(
                "google.admin_scopes",
                tenant,
                ["https://www.googleapis.com/auth/admin.directory.group"],
            ),
        )
    else:
        raise MissingConfigurationValue(
            "Missing configuration for Google. You must configure either `secrets.google.service_key_file` "
            "or `secrets.google.service_key_dict`."
        )

    # Change credential subject based on group domain
    credential_subjects = config.get_tenant_specific_key(
        "secrets.google.credential_subject", tenant
    )
    credential_subject = None
    for k, v in credential_subjects.items():
        if k == group.split("@")[1]:
            credential_subject = v
            break

    if not credential_subject:
        raise NoCredentialSubjectException(
            "Error: Unable to find Google credential subject for domain {}. "
            "{}".format(
                group.split("@")[1],
                config.get_tenant_specific_key("ses.support_reference", tenant, ""),
            )
        )

    admin_delegated_credentials = admin_credentials.with_subject(credential_subject)
    service = await aio_wrapper(
        googleapiclient.discovery.build,
        service_name,
        service_path,
        credentials=admin_delegated_credentials,
        thread_sensitive=True,
    )

    return service


async def list_group_members_call(service, email):
    return await aio_wrapper(
        service.members().list(groupKey=email).execute, thread_sensitive=True
    )


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000)
async def list_group_members(
    tenant, email: str, dry_run: None = None, service: Optional[Resource] = None
) -> List[str]:
    """List all members of a group."""
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "user": email,
        "message": "Getting list of members for group",
    }
    log.debug(log_data)
    if not service:
        service = await get_service(tenant, "admin", "directory_v1", email)

    if not dry_run:
        try:
            results = await list_group_members_call(service, email)
        except HttpError as he:
            errors = json.loads(he.content.decode())
            log.debug(errors)
            raise he
        return list(map(lambda x: x.get("email", ""), results.get("members", [])))

    return []


async def list_user_groups_call(service, user_email, page_token=None):
    if page_token:
        results = await aio_wrapper(
            service.groups().list(userKey=user_email, pageToken=page_token).execute,
            thread_sensitive=True,
        )
    else:
        results = await aio_wrapper(
            service.groups().list(userKey=user_email).execute, thread_sensitive=True
        )
    return results


async def get_group_memberships(tenant, user_email, dry_run=None, service=None):
    """Get group memberships for a user"""
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "user": user_email,
        "tenant": tenant,
        "message": "Getting list of groups for user",
    }
    log.debug(log_data)
    if not service:
        service = await get_service(tenant, "admin", "directory_v1", user_email)
    groups = []
    if not dry_run:
        try:
            page_token = None
            while True:
                results = await list_user_groups_call(service, user_email, page_token)
                for g in results.get("groups", []):
                    groups.append(g.get("email"))
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as he:
            errors = json.loads(he.content.decode())
            log.debug(errors)
            raise he
        return groups

    return []


async def raise_if_requires_bgcheck_and_no_bgcheck(
    tenant: str, user: str, group_info: Any
) -> bool:
    """Check if group requires a background check, and if the user has completed the
    background check. Will raise if the user requires a background check but has not
    completed one.
    """
    if not does_group_require_bg_check(group_info, tenant):
        return True

    user_info = await auth.get_user_info(user, object=True)

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "user": user,
        "tenant": tenant,
        "group": group_info.name,
        "backgroundcheck_required": group_info.backgroundcheck_required,
    }
    log.debug(log_data)

    if user_info.passed_background_check:
        return True
    raise BackgroundCheckNotPassedException(
        config.get_tenant_specific_key(
            "google.background_check_fail_message",
            tenant,
            "User {user} has not passed background check Group {group_name} requires a background check.",
        ).format(user=user, group_name=group_info.name)
    )


async def raise_if_not_same_domain(tenant: str, user: str, group_info: Any) -> None:
    """Check if user is in the same domain as the group. Noq will refuse to add users to groups under a different
    domain if the allow_cross_domain_users or allow_third_party_users attributes are not set to "true" for a group.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "user": user,
        "tenant": tenant,
        "group": group_info.name,
        "allow_cross_domain_users": group_info.allow_cross_domain_users,
    }
    log.debug(log_data)

    if group_info.allow_cross_domain_users:
        return True

    if group_info.allow_third_party_users:
        return True

    if user.split("@")[1] != group_info.name.split("@")[1]:
        raise DifferentUserGroupDomainException(
            config.get_tenant_specific_key(
                "google.different_domain_fail_message",
                tenant,
                "Unable to add user to a group that is in a different domain. User: {user}. Group: {group_name}",
            ).format(user=user, group_name=group_info.name)
        )


async def raise_if_restricted(tenant: str, user: str, group_info: Any) -> None:
    """Check if the group is a restricted group. Currently, Noq is not able to add users to
    restricted groups.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "user": user,
        "tenant": tenant,
        "group": group_info.name,
        "restricted": group_info.restricted,
        "compliance_restricted": group_info.compliance_restricted,
    }
    log.debug(log_data)
    if group_info.restricted:
        raise UnableToModifyRestrictedGroupMembers(
            f"Group {group_info.name} is marked as Restricted. These groups have been determined to be sensitive. "
            f"Noq cannot "
            f"currently be used to add/remove users from "
            f"restricted groups."
        )


async def raise_if_bulk_add_disabled_and_no_request(
    tenant: str, group_info: Any, request: Optional[Dict[str, Union[int, str]]]
) -> bool:
    """Check if the group has prevent_bulk_add flag. If so, a request must have been passed in for the user to be
    added to the group.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "tenant": tenant,
        "group": group_info.name,
        "request": str(request),
    }
    log.debug(log_data)
    error = config.get_tenant_specific_key(
        "google.bulk_add_disabled_fail_message",
        tenant,
        "Group {group_name} has an attribute to prevent manually adding users to it. "
        "Users must manually request access to it".format(group_name=group_info.name),
    )
    if not group_info.prevent_bulk_add:
        return True
    if not request:
        raise BulkAddPrevented(error)
    if not request["status"] == "approved":
        raise BulkAddPrevented(error)


async def insert_group_members_call(service, google_group_email, user_email, role):
    return await aio_wrapper(
        service.members()
        .insert(groupKey=google_group_email, body=dict(email=user_email, role=role))
        .execute,
        thread_sensitive=True,
    )


async def add_user_to_group(
    tenant: str,
    user_email: str,
    google_group_email: str,
    updated_by: Optional[str] = None,
    role: str = "MEMBER",
    dry_run: None = None,
    service: Optional[Resource] = None,
    request: Optional[Dict[str, Union[int, str]]] = None,
) -> Dict[str, bool]:
    """Add user member to group."""
    dynamo = UserDynamoHandler(tenant)
    result = {"done": True}
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "user_email": user_email,
        "google_group_email": google_group_email,
        "updated_by": updated_by,
        "role": role,
        "tenant": tenant,
        "dry_run": dry_run,
        "message": "Adding user to group",
    }
    if not service:
        service = await get_service(tenant, "admin", "directory_v1", google_group_email)
    existing = await list_group_members(tenant, google_group_email, dry_run=dry_run)

    if user_email in existing:
        log_data["message"] = "Unable to add user to group. User is already a member."
        log.warning(log_data)
        result["done"] = False
        result["message"] = log_data["message"]
        raise UserAlreadyAMemberOfGroupException(result["message"])

    group_info = await auth.get_group_info(tenant, google_group_email, members=False)
    await raise_if_requires_bgcheck_and_no_bgcheck(tenant, user_email, group_info)
    await raise_if_not_same_domain(tenant, user_email, group_info)
    await raise_if_restricted(tenant, user_email, group_info)
    await raise_if_bulk_add_disabled_and_no_request(tenant, group_info, request)

    if not dry_run:
        stats.count(
            "google.add_user_to_group",
            tags={
                "user_email": user_email,
                "google_group_email": google_group_email,
                "updated_by": updated_by,
                "tenant": tenant,
            },
        )

        await insert_group_members_call(service, google_group_email, user_email, role)
        await dynamo.create_group_log_entry(
            google_group_email, user_email, updated_by, "Added", tenant
        )
        log.info(log_data)
    return result


async def api_add_user_to_group_or_raise(tenant, group_name, member_name, actor):
    try:
        group_info = await auth.get_group_info(tenant, group_name, members=False)
    except Exception:
        raise NoGroupsException("Unable to retrieve the specified group")

    actor_groups = await auth.get_groups(actor)
    can_add_remove_members = can_modify_members(tenant, actor, actor_groups, group_info)

    if not can_add_remove_members:
        raise UnauthorizedToAccess("Unauthorized to modify members of this group.")

    try:
        await add_user_to_group(tenant, member_name, group_name, actor)
    except HttpError as e:
        # Inconsistent GG API error - ignore failure for user already existing
        if e.resp.reason == "duplicate":
            pass
    except UserAlreadyAMemberOfGroupException:
        pass
    except BulkAddPrevented:
        dynamo_handler = UserDynamoHandler(tenant, actor)
        dynamo_handler.add_request(
            member_name,
            group_name,
            f"{actor} requesting on behalf of {member_name} from a bulk operation",
            tenant,
            updated_by=actor,
        )
        return "REQUESTED"

    return "ADDED"


async def delete_group_members_call(service, google_group_email, user_email):
    return await aio_wrapper(
        service.members()
        .delete(groupKey=google_group_email, memberKey=user_email)
        .execute,
        thread_sensitive=True,
    )


async def remove_user_from_group(
    tenant: str,
    user_email: str,
    google_group_email: str,
    updated_by: Optional[str] = None,
    dry_run: None = None,
    service: Optional[Resource] = None,
) -> Dict[str, bool]:
    """Remove user member to group."""
    result = {"done": True}
    dynamo = UserDynamoHandler(tenant)
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    stats.count(function)
    log_data = {
        "function": function,
        "user_email": user_email,
        "group": google_group_email,
        "updated_by": updated_by,
        "dry_run": dry_run,
        "tenant": tenant,
        "message": "Removing user from group",
    }
    log.debug(log_data)

    group_info = await auth.get_group_info(tenant, google_group_email, members=False)
    await raise_if_restricted(tenant, user_email, group_info)
    if not service:
        service = await get_service(tenant, "admin", "directory_v1", google_group_email)
    existing = await list_group_members(tenant, google_group_email, dry_run=dry_run)

    if user_email in existing:
        if not dry_run:
            stats.count(
                f"{function}.remove_user_from_group",
                tags={
                    "user_email": user_email,
                    "google_group_email": google_group_email,
                    "updated_by": updated_by,
                    "tenant": tenant,
                },
            )
            await delete_group_members_call(service, google_group_email, user_email)
            await dynamo.create_group_log_entry(
                google_group_email, user_email, updated_by, "Removed", tenant
            )
    else:
        log_data[
            "message"
        ] = "Unable to remove user from group. User is not currently in the group."
        log.warning(log_data)
        result["done"] = False
        result["message"] = log_data["message"]
        raise NotAMemberException(result["message"])
    return result
