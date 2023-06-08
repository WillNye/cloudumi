# We must import models here for them to be recognized

from common.aws.accounts.models import AWSAccount  # noqa: F401,E402
from common.aws.role_access.models import (  # noqa: F401,E402
    AWSRoleAccess,
    RoleAccessTypes,
)
from common.github.models import GitHubInstall, GitHubOAuthState  # noqa: F401,E402
from common.group_memberships.models import GroupMembership  # noqa: F401,E402
from common.groups.models import Group  # noqa: F401,E402
from common.iambic.config.models import (  # noqa: F401,E402
    TenantProvider,
    TenantProviderDefinition,
)
from common.iambic.templates.models import (  # noqa: F401,E402
    IambicTemplate,
    IambicTemplateContent,
    IambicTemplateProviderDefinition,
)
from common.iambic_request.models import Request, RequestComment  # noqa: F401,E402
from common.identity.models import AwsIdentityRole  # noqa: F401,E402
from common.lib.slack.models import (  # noqa: F401,E402
    BOTS_TABLE,
    INSTALLATIONS_TABLE,
    OAUTH_STATES_TABLE,
)
from common.request_types.models import (  # noqa: F401,E402
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
    TypeAheadFieldHelper,
)
from common.tenants.models import Tenant  # noqa: F401,E402
from common.users.models import User  # noqa: F401,E402
