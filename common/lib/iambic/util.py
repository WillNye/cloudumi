from typing import List

from iambic.config.dynamic_config import Config
from iambic.core.utils import evaluate_on_provider
from iambic.plugins.v0_1_0.aws.iam.role.models import RoleAccess
from iambic.plugins.v0_1_0.aws.models import AWSAccount


def effective_accounts(
    resource: RoleAccess, aws_accounts: List[AWSAccount], config_template: Config
) -> list[AWSAccount]:
    """Evaluate a dict resource against a list of accounts and return a list of accounts that match."""
    return [
        account
        for account in aws_accounts
        if evaluate_on_provider(resource, account, None)
    ]
