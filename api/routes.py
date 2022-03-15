import os

"""Web routes."""
import pkg_resources
import sentry_sdk
import tornado.autoreload
import tornado.web
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration
from tornado.routing import HostMatches, PathMatches, Rule, RuleRouter

from api.handlers.auth import AuthHandler
from api.handlers.v1.credentials import GetCredentialsHandler
from api.handlers.v1.health import HealthHandler
from api.handlers.v1.policies import (
    ApiResourceTypeAheadHandler,
    AutocompleteHandler,
    ResourceTypeAheadHandler,
)
from api.handlers.v1.roles import GetRolesHandler
from api.handlers.v1.saml import SamlHandler
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
from api.handlers.v2.index import (
    EligibleRoleHandler,
    EligibleRolePageConfigHandler,
    EligibleRoleRefreshHandler,
    FrontendHandler,
)
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
from api.handlers.v2.terraform_resources import TerraformResourceDetailHandler
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
from api.handlers.v3.auth.sso import (
    GoogleOidcIdpConfigurationCrudHandler,
    OidcIdpConfigurationCrudHandler,
    SamlOidcIdpConfigurationCrudHandler,
)
from api.handlers.v3.downloads.weep import WeepDownloadHandler
from api.handlers.v3.integrations.aws import AwsIntegrationHandler
from api.handlers.v3.reflection import GetClientIPAddress
from api.handlers.v3.services.aws.account import (
    HubAccountHandler,
    OrgDeleteHandler,
    OrgHandler,
    SpokeDeleteHandler,
    SpokeHandler,
)
from api.handlers.v3.services.aws.ip_restrictions import (
    IpRestrictionsHandler,
    IpRestrictionsToggleHandler,
)
from api.handlers.v3.services.aws.role_access import (
    AuthorizedGroupsTagsDeleteHandler,
    AuthorizedGroupsTagsHandler,
    AutomaticPolicyUpdateHandler,
    CredentialBrokeringCurrentStateHandler,
    CredentialBrokeringHandler,
)
from api.handlers.v3.tenant_registration.tenant_registration import (
    TenantRegistrationAwsMarketplaceHandler,
    TenantRegistrationHandler,
)
from common.config import config
from common.lib.sentry import before_send_event

log = config.get_logger()


def make_app(jwt_validator=None):
    """make_app."""

    path = os.getenv("FRONTEND_PATH") or config.get(
        "_global_.web.path", pkg_resources.resource_filename("api", "templates")
    )

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
        # (r"/api/v1/myheaders/?", ApiHeaderHandler),
        (r"/api/v1/policies/typeahead", ApiResourceTypeAheadHandler),
        (r"/api/v2/policies/check", CheckPoliciesHandler),
        (r"/api/v2/dynamic_config", DynamicConfigApiHandler),
        (r"/api/v2/eligible_roles", EligibleRoleHandler),
        (r"/api/v2/eligible_roles/refresh", EligibleRoleRefreshHandler),
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
            r"/api/v2/terraform_resource/([a-zA-Z0-9_-]+)/(.*)",
            TerraformResourceDetailHandler,
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
        # (r"/myheaders/?", HeaderHandler),
        (r"/api/v2/policies/typeahead/?", ResourceTypeAheadHandler),
        (
            r"/api/v2/challenge_validator/([a-zA-Z0-9_-]+)",
            ChallengeValidatorHandler,
        ),
        (r"/noauth/v1/challenge_generator/(.*)", ChallengeGeneratorHandler),
        (r"/noauth/v1/challenge_poller/([a-zA-Z0-9_-]+)", ChallengePollerHandler),
        (r"/api/v2/audit/roles", AuditRolesHandler),
        (r"/api/v2/audit/roles/(\d{12})/(.*)/access", AuditRolesAccessHandler),
        (r"/api/v3/services/aws/account/hub", HubAccountHandler),
        (
            # (?P<param1>[^\/]+)/?(?P<param2>[^\/]+)?/?(?P<param3>[^\/]+)?
            r"/api/v3/services/aws/account/spoke/(?P<_name>[^\/]+)/(?P<_account_id>[^\/]+)/?",
            SpokeDeleteHandler,
        ),
        (r"/api/v3/services/aws/account/spoke", SpokeHandler),
        (
            r"/api/v3/services/aws/account/org/(?P<_org_id>[a-zA-Z0-9_-]+)/?",
            OrgDeleteHandler,
        ),
        (r"/api/v3/services/aws/account/org", OrgHandler),
        (
            r"/api/v3/services/aws/role-access/credential-brokering",
            CredentialBrokeringCurrentStateHandler,
        ),
        (
            r"/api/v3/services/aws/role-access/credential-brokering/(?P<_enabled>enable|disable)/?",
            CredentialBrokeringHandler,
        ),
        (
            r"/api/v3/services/aws/role-access/credential-brokering/auth-tags/?",
            AuthorizedGroupsTagsHandler,
        ),
        (
            r"/api/v3/services/aws/role-access/credential-brokering/auth-tags/(?P<_tag_name>[^\/]+)/?",
            AuthorizedGroupsTagsDeleteHandler,
        ),
        (
            r"/api/v3/services/aws/role-access/automatic-update/(?P<_enabled>enable|disable)/?",
            AutomaticPolicyUpdateHandler,
        ),
        (
            r"/api/v3/services/aws/ip-access/?",
            IpRestrictionsHandler,
        ),
        (
            r"/api/v3/services/aws/ip-access/(?P<_enabled>enable|disable)/?",
            IpRestrictionsToggleHandler,
        ),
        (
            r"/api/v3/auth/sso/google/?",
            GoogleOidcIdpConfigurationCrudHandler,
        ),
        (
            r"/api/v3/auth/sso/saml/?",
            SamlOidcIdpConfigurationCrudHandler,
        ),
        (
            r"/api/v3/auth/sso/oidc/?",
            OidcIdpConfigurationCrudHandler,
        ),
        (
            r"/api/v3/reflection/ip/?",
            GetClientIPAddress,
        ),
        (r"/api/v3/downloads/weep", WeepDownloadHandler),
        # (r"/api/v3/identities/groups_page_config", IdentityGroupPageConfigHandler),
        # (r"/api/v3/identities/groups", IdentityGroupsTableHandler),
        # (r"/api/v3/identities/users_page_config", IdentityUsersPageConfigHandler),
        # (r"/api/v3/identities/users", IdentityUsersTableHandler),
        # (r"/api/v3/identities/requests", IdentityRequestsTableHandler),
        # (r"/api/v3/identities/group/(.*?)/(.*)", IdentityGroupHandler),
        # (r"/api/v3/identities/user/(.*?)/(.*)", IdentityUserHandler),
        # (r"/api/v3/identities/group_requests/(.*)", IdentityGroupRequestReviewHandler),
        # (r"/api/v3/identities/requests/group/(.*?)/(.*)", IdentityRequestGroupHandler),
        # (r"/api/v3/identities/requests/groups", IdentityRequestGroupsHandler),
        # # (r"/api/v3/identities/requests/user/(.*?)/(.*)", IdentityRequestUserHandler),
        # (r"/api/v3/identities/requests_page_config", IdentityRequestsPageConfigHandler),
        (r"/api/v3/integrations/aws", AwsIntegrationHandler),
        # (r"/api/v3/tasks", TasksHandler),
        # (r"/api/v3/config", ConfigHandler),
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
                [
                    (r"/api/v3/tenant_registration", TenantRegistrationHandler),
                    (
                        r"/api/v3/tenant_registration_aws_marketplace",
                        TenantRegistrationAwsMarketplaceHandler,
                    ),
                ],
            )
        )
    router.rules.append(
        Rule(
            PathMatches(r"/(.*)"),
            FrontendHandler,
            dict(path=path, default_filename="index.html"),
        ),
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
            before_send=before_send_event,
            traces_sample_rate=config.get("_global_.sentry.traces_sample_rate", 0.2),
            integrations=[
                TornadoIntegration(),
                AioHttpIntegration(),
                RedisIntegration(),
            ],
        )

    return app
