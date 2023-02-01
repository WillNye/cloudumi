from typing import List

from iambic.aws.iam.role.models import RoleAccess

from common.aws.accounts.models import AWSAccount


def effective_accounts(
    resource: RoleAccess, aws_accounts: List[AWSAccount]
) -> List[AWSAccount]:
    """Evaluate a dict resource against a list of accounts and return a list of accounts that match."""
    if resource.included_accounts == ["*"]:
        included_accounts = aws_accounts
    else:
        included_accounts = [
            aws_account
            for aws_account in aws_accounts
            if aws_account.number in resource.included_accounts
            or aws_account.name in resource.included_accounts
        ]
    if resource.excluded_accounts == ["*"]:
        return []
    else:
        excluded_accounts = [
            aws_account
            for aws_account in aws_accounts
            if aws_account.number in resource.excluded_accounts
            or aws_account.name in resource.excluded_accounts
        ]

    return {
        account for account in included_accounts if account not in excluded_accounts
    }
