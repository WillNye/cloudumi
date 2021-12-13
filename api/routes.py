"""Web routes."""

import sentry_sdk
import tornado.autoreload
import tornado.web
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration
from tornado.routing import HostMatches, Rule, RuleRouter

from api.handlers.auth import AuthHandler
from api.handlers.v1.credentials import GetCredentialsHandler
from api.handlers.v1.headers import ApiHeaderHandler, HeaderHandler
from api.handlers.v1.health import HealthHandler
from api.handlers.v1.policies import (
    ApiResourceTypeAheadHandler,
    AutocompleteHandler,
    ResourceTypeAheadHandler,
)
from api.handlers.v1.roles import GetRolesHandler
from api.handlers.v2.audit import AuditRolesAccessHandler, AuditRolesHandler
from api.handlers.v2.aws_iam_users import UserDetailHandler
from api.handlers.v2.challenge import (
    ChallengeGeneratorHandler,
    ChallengePollerHandler,
    ChallengeValidatorHandler,
)
from api.handlers.v2.dynamic_config import DynamicConfigApiHandler
from api.handlers.v2.errors import NotFoundHandler as V2NotFoundHandler
from api.handlers.v2.generate_changes import GenerateChangesHandler
from api.handlers.v2.generate_policy import GeneratePolicyHandler
from api.handlers.v2.index import EligibleRoleHandler, EligibleRolePageConfigHandler
from api.handlers.v2.logout import LogOutHandler
from api.handlers.v2.managed_policies import (
    ManagedPoliciesForAccountHandler,
    ManagedPoliciesHandler,
    ManagedPoliciesOnPrincipalHandler,
)
from api.handlers.v2.notifications import NotificationsHandler
from api.handlers.v2.policies import (
    CheckPoliciesHandler,
    PoliciesHandler,
    PoliciesPageConfigHandler,
)
from api.handlers.v2.requests import (
    RequestDetailHandler,
    RequestHandler,
    RequestsHandler,
    RequestsPageConfigHandler,
)
from api.handlers.v2.resources import GetResourceURLHandler, ResourceDetailHandler
from api.handlers.v2.roles import (
    AccountRolesHandler,
    GetRolesMTLSHandler,
    RoleCloneHandler,
    RoleConsoleLoginHandler,
    RoleDetailAppHandler,
    RoleDetailHandler,
    RolesHandler,
)
from api.handlers.v2.self_service import (
    PermissionTemplatesHandler,
    SelfServiceConfigHandler,
)
from api.handlers.v2.service_control_policy import ServiceControlPolicyHandler
from api.handlers.v2.templated_resources import TemplatedResourceDetailHandler
from api.handlers.v2.typeahead import (
    ResourceTypeAheadHandlerV2,
    SelfServiceStep1ResourceTypeahead,
)
from api.handlers.v2.user import (
    LoginConfigurationHandler,
    LoginHandler,
    UserManagementHandler,
    UserRegistrationHandler,
)
from api.handlers.v2.user_profile import UserProfileHandler
from api.handlers.v3.identity.group import IdentityGroupHandler
from api.handlers.v3.identity.groups import (
    IdentityGroupPageConfigHandler,
    IdentityGroupsTableHandler,
)
from api.handlers.v3.identity.requests.group import (
    IdentityGroupRequestReviewHandler,
    IdentityRequestGroupHandler,
    IdentityRequestGroupsHandler,
)
from api.handlers.v3.identity.requests.table import (
    IdentityRequestsPageConfigHandler,
    IdentityRequestsTableHandler,
)
from api.handlers.v3.identity.users import (
    IdentityUserHandler,
    IdentityUsersPageConfigHandler,
    IdentityUsersTableHandler,
)
from api.handlers.v3.integrations.aws import AwsIntegrationHandler
from api.handlers.v3.tenant_registration.tenant_registration import (
    TenantRegistrationHandler,
)
from common.config import config
from saml.handlers.v1.saml import SamlHandler

log = config.get_logger()


def make_app(jwt_validator=None):
    """make_app."""

    routes = [
        (r"/auth", AuthHandler),  # /auth is still used by OIDC callback
        (r"/saml/(.*)", SamlHandler),
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
        (r"/api/v3/identities/groups_page_config", IdentityGroupPageConfigHandler),
        (r"/api/v3/identities/groups", IdentityGroupsTableHandler),
        (r"/api/v3/identities/users_page_config", IdentityUsersPageConfigHandler),
        (r"/api/v3/identities/users", IdentityUsersTableHandler),
        (r"/api/v3/identities/requests", IdentityRequestsTableHandler),
        (r"/api/v3/identities/group/(.*?)/(.*)", IdentityGroupHandler),
        (r"/api/v3/identities/user/(.*?)/(.*)", IdentityUserHandler),
        (r"/api/v3/identities/group_requests/(.*)", IdentityGroupRequestReviewHandler),
        (r"/api/v3/identities/requests/group/(.*?)/(.*)", IdentityRequestGroupHandler),
        (r"/api/v3/identities/requests/groups", IdentityRequestGroupsHandler),
        # (r"/api/v3/identities/requests/user/(.*?)/(.*)", IdentityRequestUserHandler),
        (r"/api/v3/identities/requests_page_config", IdentityRequestsPageConfigHandler),
        (r"/api/v3/integrations/aws", AwsIntegrationHandler),
        # (r"/api/v3/api_keys/add", AddApiKeyHandler),
        # (r"/api/v3/api_keys/remove", RemoveApiKeyHandler),
        # (r"/api/v3/api_keys/view", ViewApiKeysHandler),
        (r"/api/v2/.*", V2NotFoundHandler),
    ]

    router = RuleRouter(routes)
    for domain in config.get("_global_.landing_page_domains", []):
        router.rules.append(
            Rule(
                HostMatches(domain),
                [(r"/api/v3/tenant_registration", TenantRegistrationHandler)],
            )
        )

    app = tornado.web.Application(
        router.rules,
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
