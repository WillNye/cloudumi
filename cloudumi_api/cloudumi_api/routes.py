"""Web routes."""

import sentry_sdk
import tornado.autoreload
import tornado.web
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration

from cloudumi_api.handlers.auth import AuthHandler
from cloudumi_api.handlers.v1.credentials import GetCredentialsHandler
from cloudumi_api.handlers.v1.headers import ApiHeaderHandler, HeaderHandler
from cloudumi_api.handlers.v1.health import HealthHandler
from cloudumi_api.handlers.v1.policies import (
    ApiResourceTypeAheadHandler,
    AutocompleteHandler,
    ResourceTypeAheadHandler,
)
from cloudumi_api.handlers.v1.roles import GetRolesHandler
from cloudumi_api.handlers.v2.audit import AuditRolesAccessHandler, AuditRolesHandler
from cloudumi_api.handlers.v2.aws_iam_users import UserDetailHandler
from cloudumi_api.handlers.v2.challenge import (
    ChallengeGeneratorHandler,
    ChallengePollerHandler,
    ChallengeValidatorHandler,
)
from cloudumi_api.handlers.v2.dynamic_config import DynamicConfigApiHandler
from cloudumi_api.handlers.v2.errors import NotFoundHandler as V2NotFoundHandler
from cloudumi_api.handlers.v2.generate_changes import GenerateChangesHandler
from cloudumi_api.handlers.v2.generate_policy import GeneratePolicyHandler
from cloudumi_api.handlers.v2.index import (
    EligibleRoleHandler,
    EligibleRolePageConfigHandler,
)
from cloudumi_api.handlers.v2.logout import LogOutHandler
from cloudumi_api.handlers.v2.managed_policies import (
    ManagedPoliciesForAccountHandler,
    ManagedPoliciesHandler,
    ManagedPoliciesOnPrincipalHandler,
)
from cloudumi_api.handlers.v2.notifications import NotificationsHandler
from cloudumi_api.handlers.v2.policies import (
    CheckPoliciesHandler,
    PoliciesHandler,
    PoliciesPageConfigHandler,
)
from cloudumi_api.handlers.v2.requests import (
    RequestDetailHandler,
    RequestHandler,
    RequestsHandler,
    RequestsPageConfigHandler,
)
from cloudumi_api.handlers.v2.resources import (
    GetResourceURLHandler,
    ResourceDetailHandler,
)
from cloudumi_api.handlers.v2.roles import (
    AccountRolesHandler,
    GetRolesMTLSHandler,
    RoleCloneHandler,
    RoleConsoleLoginHandler,
    RoleDetailAppHandler,
    RoleDetailHandler,
    RolesHandler,
)
from cloudumi_api.handlers.v2.self_service import (
    PermissionTemplatesHandler,
    SelfServiceConfigHandler,
)
from cloudumi_api.handlers.v2.service_control_policy import ServiceControlPolicyHandler
from cloudumi_api.handlers.v2.templated_resources import TemplatedResourceDetailHandler
from cloudumi_api.handlers.v2.typeahead import (
    ResourceTypeAheadHandlerV2,
    SelfServiceStep1ResourceTypeahead,
)
from cloudumi_api.handlers.v2.user import (
    LoginConfigurationHandler,
    LoginHandler,
    UserManagementHandler,
    UserRegistrationHandler,
)
from cloudumi_api.handlers.v2.user_profile import UserProfileHandler
from cloudumi_api.handlers.v3.identity.group import IdentityGroupHandler
from cloudumi_api.handlers.v3.identity.groups import (
    IdentityGroupPageConfigHandler,
    IdentityGroupsTableHandler,
)
from cloudumi_api.handlers.v3.identity.requests.group import (
    IdentityGroupRequestReviewHandler,
    IdentityRequestGroupHandler,
)
from cloudumi_common.config import config

log = config.get_logger()


def make_app(jwt_validator=None):
    """make_app."""

    routes = [
        (r"/auth", AuthHandler),  # /auth is still used by OIDC callback
        (r"/healthcheck", HealthHandler),
        (r"/api/v1/auth", AuthHandler),
        (r"/api/v1/get_credentials", GetCredentialsHandler),
        (r"/api/v1/get_roles", GetRolesHandler),
        (r"/api/v2/get_roles", GetRolesMTLSHandler),
        (r"/api/v2/get_resource_url", GetResourceURLHandler),
        # Used to autocomplete AWS permissions
        (r"/api/v1/policyuniverse/autocomplete/?", AutocompleteHandler),
        (r"/api/v2/user_profile/?", UserProfileHandler),
        (r"/api/v2/self_service_config/?", SelfServiceConfigHandler),
        (r"/api/v2/permission_templates/?", PermissionTemplatesHandler),
        (r"/api/v1/myheaders/?", ApiHeaderHandler),
        (r"/api/v1/policies/typeahead", ApiResourceTypeAheadHandler),
        (r"/api/v2/policies/check", CheckPoliciesHandler),
        (r"/api/v2/dynamic_config", DynamicConfigApiHandler),
        (r"/api/v2/eligible_roles", EligibleRoleHandler),
        (r"/api/v2/eligible_roles_page_config", EligibleRolePageConfigHandler),
        (r"/api/v2/policies_page_config", PoliciesPageConfigHandler),
        (r"/api/v2/requests_page_config", RequestsPageConfigHandler),
        (r"/api/v2/generate_policy", GeneratePolicyHandler),
        (r"/api/v2/notifications/?", NotificationsHandler),
        (r"/api/v2/managed_policies/(\d{12})", ManagedPoliciesForAccountHandler),
        (r"/api/v2/managed_policies/(.*)", ManagedPoliciesHandler),
        (
            r"/api/v2/templated_resource/([a-zA-Z0-9_-]+)/(.*)",
            TemplatedResourceDetailHandler,
        ),
        (
            r"/api/v2/managed_policies_on_principal/(.*)",
            ManagedPoliciesOnPrincipalHandler,
        ),
        (r"/api/v2/login", LoginHandler),
        (r"/api/v2/login_configuration", LoginConfigurationHandler),
        (r"/api/v2/logout", LogOutHandler),
        (
            r"/api/v2/typeahead/self_service_resources",
            SelfServiceStep1ResourceTypeahead,
        ),
        (r"/api/v2/user", UserManagementHandler),
        (r"/api/v2/user_registration", UserRegistrationHandler),
        (r"/api/v2/policies", PoliciesHandler),
        (r"/api/v2/request", RequestHandler),
        (r"/api/v2/requests", RequestsHandler),
        (r"/api/v2/requests/([a-zA-Z0-9_-]+)", RequestDetailHandler),
        (r"/api/v2/roles/?", RolesHandler),
        (r"/api/v2/roles/(\d{12})", AccountRolesHandler),
        (r"/api/v2/roles/(\d{12})/(.*)", RoleDetailHandler),
        (r"/api/v2/users/(\d{12})/(.*)", UserDetailHandler),
        (
            r"/api/v2/resources/(\d{12})/(s3|sqs|sns|managed_policy)(?:/([a-z\-1-9]+))?/(.*)",
            ResourceDetailHandler,
        ),
        (r"/api/v2/service_control_policies/(.*)", ServiceControlPolicyHandler),
        (r"/api/v2/mtls/roles/(\d{12})/(.*)", RoleDetailAppHandler),
        (r"/api/v2/clone/role", RoleCloneHandler),
        (r"/api/v2/generate_changes/?", GenerateChangesHandler),
        (r"/api/v2/typeahead/resources", ResourceTypeAheadHandlerV2),
        (r"/api/v2/role_login/(.*)", RoleConsoleLoginHandler),
        (r"/myheaders/?", HeaderHandler),
        (r"/api/v2/policies/typeahead/?", ResourceTypeAheadHandler),
        (
            r"/api/v2/challenge_validator/([a-zA-Z0-9_-]+)",
            ChallengeValidatorHandler,
        ),
        (r"/noauth/v1/challenge_generator/(.*)", ChallengeGeneratorHandler),
        (r"/noauth/v1/challenge_poller/([a-zA-Z0-9_-]+)", ChallengePollerHandler),
        (r"/api/v2/audit/roles", AuditRolesHandler),
        (r"/api/v2/audit/roles/(\d{12})/(.*)/access", AuditRolesAccessHandler),
        (r"/api/v3/identity_groups_page_config", IdentityGroupPageConfigHandler),
        (r"/api/v3/identities/groups", IdentityGroupsTableHandler),
        (r"/api/v3/identities/group/(.*?)/(.*)", IdentityGroupHandler),
        (r"/api/v3/identities/group_requests/(.*)", IdentityGroupRequestReviewHandler),
        (r"/api/v3/identities/requests/group/(.*?)/(.*)", IdentityRequestGroupHandler),
        (r"/api/v2/.*", V2NotFoundHandler),
    ]

    app = tornado.web.Application(
        routes,
        debug=config.get("_global_.tornado.debug", False),
        xsrf_cookies=config.get("_global_.tornado.xsrf", True),
        xsrf_cookie_kwargs=config.get("_global_.tornado.xsrf_cookie_kwargs", {}),
    )
    sentry_dsn = config.get("_global_.sentry.dsn")

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                TornadoIntegration(),
                AioHttpIntegration(),
                RedisIntegration(),
            ],
        )

    return app
