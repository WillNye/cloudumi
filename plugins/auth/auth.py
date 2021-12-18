import sys
import time
from typing import List

import ujson as json

from common.config import config
from common.exceptions.exceptions import (
    InvalidCertificateException,
    MissingConfigurationValue,
    NoUserException,
)
from common.lib.generic import str2bool
from common.lib.plugins import get_plugin_by_name

log = config.get_logger("consoleme")
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


class Group(object):
    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name")
        self.domain: str = kwargs.get("domain")
        self.group_id: str = kwargs.get("groupId")
        self.friendly_name: str = kwargs.get("friendlyName")
        self.description: str = kwargs.get("description")
        self.settings: str = kwargs.get("settings")
        self.aliases: str = kwargs.get("aliases")
        self.members: List = kwargs.get("members", [])
        self.attributes: List = kwargs.get("attributes")
        self.automated_group: bool = self.is_group_automated(self.description)

        # Set all boolean attributes
        for attr in config.get("_global_.groups.attributes.boolean", []):
            attribute_name = attr.get("name")
            setattr(self, attribute_name, str2bool(kwargs.get(attribute_name)))

        # Set all list attributes
        for attr in config.get("_global_.groups.attributes.list", []):
            attribute_name = attr.get("name")
            setattr(self, attribute_name, self.convert_to_list(kwargs, attribute_name))

    def get(self, query, default=None):
        result = self.__dict__.get(query)
        if result is None:
            result = default
        return result

    @staticmethod
    def convert_to_list(kwargs, kwarg):
        if kwargs.get(kwarg):
            return kwargs[kwarg].split(",")
        return []

    @staticmethod
    def is_group_automated(description):
        return False


class User(object):
    def __init__(self, **kwargs):
        self.username: str = kwargs.get("userName")
        self.domain: str = kwargs.get("domain")
        self.fullname: str = kwargs.get("name", {}).get("fullName")
        self.status: str = kwargs.get("status")
        self.created: str = kwargs.get("created", {}).get("onDate")
        self.updated: str = kwargs.get("updated", {}).get("onDate")
        self.groups: str = kwargs.get("members")
        self.passed_background_check: bool = str2bool(
            kwargs.get("passed_background_check", False)
        )

    def get(self, query):
        return self.__dict__.get(query)

    def to_json(self):
        d = {
            "username": self.username,
            "domain": self.domain,
            "fullname": self.fullname,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
            "groups": self.groups,
            "passed_background_check": self.passed_background_check,
        }
        return json.dumps(d)


class ExtendedAttribute(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.type = kwargs.get("attributeType", "string")
        self.value = kwargs.get("attributeValue")
        if self.value is True:
            self.value = "true"
        elif self.value is False:
            self.value = "false"
        self.sensitive = kwargs.get("sensitive", False)
        self.immutable = kwargs.get("immutable", False)

    def get(self, query):
        return self.__dict__.get(query)

    def to_json(self):
        if isinstance(self.value, list):
            self.value = ",".join(self.value)
        d = {
            "name": self.name,
            "attributeType": self.type,
            "attributeValue": self.value,
            "sensitive": self.sensitive,
            "immutable": self.immutable,
        }
        return json.dumps(d)


class Auth:
    """The Auth class authenticates the user and provides the user's groups."""

    def __init__(self, headers: dict = None):
        """Initialize the auth class."""
        self.headers = headers

    async def get_user(self, request_object):
        """Get the user identity."""
        host = request_object.get_host_name()
        headers = request_object.request.headers
        if config.get_host_specific_key(
            f"site_configs.{host}.auth.get_user_by_header", host
        ):
            return await self.get_user_by_header(headers, request_object)
        else:
            raise Exception("auth.get_user not configured")

    async def get_user_by_header(self, headers: dict, request_object):
        """Get the user identity via plaintext header."""
        host = request_object.get_host_name()
        if not headers:
            raise Exception(
                f"site_configs.{host}.auth.get_user_by_header enabled, but no headers were passed in"
            )

        user_header_name = config.get_host_specific_key(
            f"site_configs.{host}.auth.user_header_name", host
        )
        if not user_header_name:
            raise Exception(
                f"site_configs.{host}.auth.user_header_name configuration not set, but auth.get_user_by_header is enabled."
            )

        user = headers.get(user_header_name)
        if not user:
            raise NoUserException("User header '{}' is empty.".format(user_header_name))
        return user

    async def get_groups(
        self,
        user: str,
        request_object,
        headers=None,
        get_header_groups=False,
        only_direct=True,
    ):
        """Get the user's groups."""
        host = request_object.get_host_name()
        groups_to_add_for_all_users = config.get_host_specific_key(
            f"site_configs.{host}.auth.groups_to_add_for_all_users", host, []
        )
        groups = []
        if get_header_groups or config.get_host_specific_key(
            f"site_configs.{host}.auth.get_groups_by_header", host
        ):
            header_groups = await self.get_groups_by_header(headers, request_object)
            if header_groups:
                groups.extend(header_groups)
        elif config.get_host_specific_key(
            f"site_configs.{host}.auth.get_groups_from_google", host
        ):
            from common.lib.google import get_group_memberships

            google_groups = await get_group_memberships(host, user)
            if google_groups:
                groups.extend(google_groups)
        if groups_to_add_for_all_users:
            # Optionally consider ConsoleMe users a member of these additional groups
            groups.extend(groups_to_add_for_all_users)
        if not groups:
            log.error(
                {
                    "message": f"site_configs.{host}.auth.get_groups not configured properly or no groups were obtained."
                },
                exc_info=True,
            )
        if config.get_host_specific_key(
            f"site_configs.{host}.auth.force_groups_lowercase", host, False
        ):
            groups = [x.lower() for x in groups]
        return list(set(groups))

    async def get_groups_by_header(self, headers: dict, request_object):
        """Get the user's groups by plaintext header."""
        host = request_object.get_host_name()
        groups = []

        if not headers:
            log_data = {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "No headers present.",
            }
            log.debug(log_data, exc_info=True)
            return groups

        groups_header_name = config.get_host_specific_key(
            f"site_configs.{host}.auth.groups_header_name", host, None
        )
        if not groups_header_name:
            log_data = {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Group header name not configured.",
            }
            log.debug(log_data, exc_info=True)
            raise Exception(
                f"site_configs.{host}.auth.groups_header_name configuration not set, but "
                "auth.get_groups_by_header is enabled."
            )

        if headers.get(groups_header_name):
            groups = headers[groups_header_name].split(",")

        return groups

    async def extract_certificate(self, headers: dict):
        raise NotImplementedError()

    async def extract_user_from_certificate(self, headers: dict):
        return await self.extract_certificate(headers)

    async def get_cert_age_seconds(self, headers: dict):
        """Retrieve age of mtls certificate."""
        current_time = int(time.time())
        cert = await self.extract_certificate(headers)
        return current_time - int(cert.get("notBefore"))

    async def validate_certificate(self, request_object):
        headers = request_object.request.headers
        host = request_object.get_host_name()
        cli_auth_required_headers = config.get_host_specific_key(
            f"site_configs.{host}.cli_auth.required_headers", host
        )
        if not cli_auth_required_headers:
            raise MissingConfigurationValue(
                "You must specified the header key and expected value in order to validate a certificate for mutual "
                f"TLS authentication. Refer to the `site_configs.{host}.cli_auth.required_headers` configuration"
            )
        for header in cli_auth_required_headers:
            for k, v in header.items():
                if headers.get(k) != v:
                    stats.count("auth.validate_certificate.error")
                    error = (
                        "Header {} is supposed to equal {}, but it equals {}.".format(
                            k, v, headers.get(k)
                        )
                    )
                    log_data = {
                        "function": "auth.validate_certificate",
                        "message": error,
                    }
                    log.error(log_data)
                    raise InvalidCertificateException(error)
        return True

    async def is_user_contractor(self, user):
        return False

    async def validate_and_return_api_caller(self, headers: dict, host: str):
        cli_auth_required_headers = config.get_host_specific_key(
            f"site_configs.{host}.cli_auth.required_headers", host
        )
        if not cli_auth_required_headers:
            raise MissingConfigurationValue(
                "You must specified the header key and expected value in order to validate a certificate for mutual "
                "TLS authentication. Refer to the `cli_auth.required_headers` configuration"
            )
        for header in cli_auth_required_headers:
            for k, v in header.items():
                if headers.get(k) != v:
                    raise Exception(
                        f"Header {k} is supposed to equal {v}, but it equals {headers.get(k)}."
                    )
        cert = await self.extract_user_from_certificate(headers)
        user = cert.get("name")
        if not user or user not in config.get_host_specific_key(
            f"site_configs.{host}.api_auth.valid_entities", host, []
        ):
            raise Exception("Not authorized to call this API with that certificate.")
        return user

    async def get_user_info(self, user: str, host: str, object: bool = False):
        """
        Retrieve details about a user from an authorative source
        :param user:
        :param object:
        :return:
        """
        return {
            "domain": "",
            "userName": user,
            "name": {
                "givenName": "",
                "familyName": "",
                "fullName": "",
            },
            "primaryEmail": user,
        }

    async def get_group_info(self, host, group, members=True):
        raise NotImplementedError()

    async def put_group_attribute(self, group, attribute_name, attribute_value):
        raise NotImplementedError()

    async def put_group_attributes(self, group, attributes):
        raise NotImplementedError()

    async def is_user_in_group(self, user, group, only_direct=True):
        raise NotImplementedError()

    async def is_requestable(self, group):
        raise NotImplementedError()

    async def does_user_exist(self, host, user):
        raise NotImplementedError()

    async def get_group_attribute(self, group, attribute_name):
        raise NotImplementedError()

    async def get_secondary_approvers(self, group, host):
        """Return a list of secondary approvers for a group."""
        raise NotImplementedError()

    async def get_groups_with_attribute_name_value(
        self, attribute_name, attribute_value
    ):
        raise NotImplementedError()

    async def get_users_with_attribute_name_value(
        self, attribute_name, attribute_value
    ):
        raise NotImplementedError()

    async def is_group_requestable(self, group):
        raise NotImplementedError()

    async def get_all_requestable_groups(self):
        raise NotImplementedError()

    async def get_group_memberships(self, user, scopes=[], only_direct=True) -> list:
        return []

    async def get_group_members(self, group):
        raise NotImplementedError()

    async def get_user_attribute(self, user, attribute_name):
        raise NotImplementedError()

    async def get_or_create_user_role_name(self, user):
        user_role_name_attribute = await self.get_user_attribute(user, "user_role_name")
        if not user_role_name_attribute:
            return await self.generate_and_store_user_role_name(user)
        user_role_name = user_role_name_attribute.value
        return user_role_name

    async def generate_and_store_user_role_name(self, user):
        (username, domain) = user.split("@")
        return f"{username}-{domain}"


Auth.Group = Group
Auth.User = User
Auth.ExtendedAttribute = ExtendedAttribute


def init():
    """Initialize the auth plugin."""
    return Auth()
