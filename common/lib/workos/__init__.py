from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pytz
import workos
from furl import furl

from common.config.tenant_config import TenantConfig
from common.exceptions.exceptions import WorkOSNoOrganizationId
from common.lib.asyncio import aio_wrapper
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.generic import should_force_redirect
from common.lib.jwt import generate_jwt_token


class WorkOS:
    def __init__(self, tenant: str):
        self.tenant = tenant
        self.tenant_config = TenantConfig(tenant)
        self.api_key = self.tenant_config.workos_api_key
        self.client_id = self.tenant_config.workos_client_id
        workos.api_key = self.api_key
        workos.client_id = self.client_id
        self.workos_client = workos.client
        self.workos_client.api_key = self.api_key
        self.workos_client.client_id = self.client_id

    async def create_organization(self, allowed_domains: list[str]):
        organization = self.workos_client.organizations.create_organization(
            {
                "name": self.tenant,
                "allow_profiles_outside_organization": False,
                "domains": allowed_domains,
            }
        )
        return organization

    async def cache_users_from_directory(self):
        directories_synced = 0
        users_synced = 0
        user_groups_synced = 0
        directories = await aio_wrapper(
            self.workos_client.directory_sync.list_directories
        )
        for directory in directories.get("data", []):
            tenant = directory["name"]
            if tenant != self.tenant:
                continue
            directories_synced += 1
            user_to_group_mapping = defaultdict(defaultdict)
            directory_id = directory["id"]
            users_from_directory = await aio_wrapper(
                self.workos_client.directory_sync.list_users, directory=directory_id
            )

            for user in users_from_directory.get("data", []):
                users_synced += 1
                raw_groups = user.get("groups", [])
                group_names = [g.get("name") for g in raw_groups]
                group_emails = [
                    g.get("raw_attributes", {}).get("email", "") for g in raw_groups
                ]
                user_groups_synced += len(group_names)
                user_to_group_mapping[user["username"]] = {
                    "group_names": group_names,
                    "group_emails": group_emails,
                }

            await store_json_results_in_redis_and_s3(
                user_to_group_mapping,
                redis_key=self.tenant_config.workos_redis_key,
                s3_key=self.tenant_config.workos_s3_key,
                tenant=tenant,
            )
        return {
            "directories_synced": directories_synced,
            "users_synced": users_synced,
            "user_groups_synced": user_groups_synced,
        }

    async def retrieve_user_groups(self, user: str, tenant: str) -> list[str]:
        user_to_group_mapping = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.workos_redis_key,
            s3_key=self.tenant_config.workos_s3_key,
            tenant=tenant,
        )
        return user_to_group_mapping.get(user, {}).get(
            self.tenant_config.workos_group_attribute, []
        )

    async def retrieve_organization_id(self) -> Optional[str]:
        organizations = await aio_wrapper(
            self.workos_client.organizations.list_organizations
        )
        for organization in organizations.get("data", []):
            if organization["name"] == self.tenant:
                return organization["id"]
        return None

    async def get_after_redirect_uri(
        self, request, force_redirect: bool
    ) -> Tuple[str, Optional[str]]:
        after_redirect_uri = request.request.arguments.get("redirect_url", [""])[0]
        if not after_redirect_uri:
            after_redirect_uri = request.request.arguments.get("state", [""])[0]
        if after_redirect_uri and isinstance(after_redirect_uri, bytes):
            after_redirect_uri = after_redirect_uri.decode("utf-8")
        if not after_redirect_uri and force_redirect:
            # If we're forcing a redirect, we need to redirect to the same page.
            after_redirect_uri = request.request.uri
        if not after_redirect_uri:
            after_redirect_uri = self.tenant_config.tenant_url

        code = request.get_argument("code", None)

        if not code:
            parsed_after_redirect_uri = furl(after_redirect_uri)
            code = parsed_after_redirect_uri.args.get("code")
            if code:
                del parsed_after_redirect_uri.args["code"]
            after_redirect_uri = parsed_after_redirect_uri.url

        return (after_redirect_uri, code)

    async def authenticate_user_by_workos(self, request):
        full_host = request.request.headers.get("X-Forwarded-Host")
        if not full_host:
            full_host = request.get_tenant()
        force_redirect = await should_force_redirect(request.request)
        organization_id = await self.retrieve_organization_id()
        if not organization_id:
            raise WorkOSNoOrganizationId(
                f"Could not find organization id for tenant {self.tenant}"
            )

        # The endpoint where the user wants to be sent after authentication.
        # This will be stored in the state.
        after_redirect_uri, code = await self.get_after_redirect_uri_and_code(request)

        if not code:
            authorization_url = await aio_wrapper(
                self.workos_client.sso.get_authorization_url,
                organization=organization_id,
                redirect_uri=self.tenant_config.tenant_url,
            )
            if force_redirect:
                request.redirect(authorization_url)
            else:
                request.set_status(403)
                request.write(
                    {
                        "type": "redirect",
                        "redirect_url": authorization_url,
                        "reason": "unauthenticated",
                        "message": "User is not authenticated. Redirect to authenticate",
                    }
                )
            request.finish()
            return

        profile_and_token = await aio_wrapper(
            self.workos_client.sso.get_profile_and_token, code
        )
        email = profile_and_token.profile.email
        groups = await self.retrieve_user_groups(email, self.tenant)
        expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
            minutes=self.tenant_config.auth_jwt_expiration_minutes
        )

        encoded_cookie = await generate_jwt_token(
            email,
            groups,
            self.tenant,
            exp=expiration,
            mfa_setup_required=None,
        )

        request.set_cookie(
            self.tenant_config.auth_cookie_name,
            encoded_cookie,
            expires=expiration,
            secure=self.tenant_config.auth_use_secure_cookies,
            httponly=self.tenant_config.auth_cookie_httponly,
            samesite=self.tenant_config.auth_cookie_samesite,
        )
        if force_redirect:
            request.redirect(after_redirect_uri)
        else:
            request.set_status(403)
            request.write(
                {
                    "type": "redirect",
                    "redirect_url": after_redirect_uri,
                    "reason": "unauthenticated",
                    "message": "User has been authenticated and needs to be redirected to their intended destination",
                }
            )
        request.finish()
        return
