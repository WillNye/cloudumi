from typing import List

from iambic.aws.iam.role.models import RoleAccess
from iambic.config.models import Config
from iambic.core.utils import evaluate_on_provider

from common.aws.accounts.models import AWSAccount


def effective_accounts(
    resource: RoleAccess, aws_accounts: List[AWSAccount], config_template: Config
) -> List[AWSAccount]:
    """Evaluate a dict resource against a list of accounts and return a list of accounts that match."""
    iambic_accounts = [
        y
        for y in config_template.aws.accounts
        for x in aws_accounts
        if y.account_name == x.name and y.account_id == x.account_id
    ]
    effective_iambic_accounts = [
        account
        for account in iambic_accounts
        if evaluate_on_provider(resource, account, None)
    ]
    return {
        x
        for x in aws_accounts
        if x.account_id in [y.account_id for y in effective_iambic_accounts]
        and x.name in [y.account_name for y in effective_iambic_accounts]
    }