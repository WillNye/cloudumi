import asyncio
import re
from collections import defaultdict
from typing import Any

# Combining statements with these elements may have unintended consequences
IGNORE_STATEMENTS_WITH = ["Condition", "NotAction", "NotPrincipal", "NotResource"]


def get_regex_resource_names(statement: dict) -> list:
    """Generates a list of resource names for a statement that can be used for regex searches

    :param statement: A statement, IE: {
        'Action': ['s3:listbucket', 's3:list*'],
        'Effect': 'Allow',
        'Resource': ["arn:aws:dynamodb:*:*:table/TableOne", "arn:aws:dynamodb:*:*:table/TableTwo"]
    }
    :return: A list of resource names to be used for regex checks, IE: [
        "Allow:arn:aws:dynamodb:.*:.*:table/Table", "Allow:arn:aws:dynamodb:.*:.*:table/Table"
    ]
    """
    return [
        f"{statement.get('Effect')}:{resource}".replace("*", ".*")
        for resource in statement.get("Resource")
    ]


async def is_resource_match(regex_patterns, regex_strs) -> bool:
    """Check if all provided strings (regex_strs) match on AT LEAST ONE regex pattern

    :param regex_patterns: A list of regex patterns to search on
    :param regex_strs: A list of strings to check against
    """

    async def _regex_check(regex_pattern) -> bool:
        return any(re.match(regex_pattern, regex_str) for regex_str in regex_strs)

    results = await asyncio.gather(
        *[_regex_check(regex_pattern) for regex_pattern in regex_patterns]
    )
    return all(r for r in results)


async def is_action_match(
    action_map: dict[list], comparable_action_map: dict[list]
) -> bool:
    for service, actions in action_map.items():
        comp_actions = comparable_action_map.get(service)
        if not comp_actions or not all(action in comp_actions for action in actions):
            return False

    return True


async def reduce_statement_actions(statement: dict) -> dict:
    """Removes redundant actions from a statement and stores a regex map of the reduced.

    :param statement: A normalized statement, IE: {
        'Action': ['s3:listbucket', 's3:list*'], 'Effect': 'Allow', 'Resource': ['*']
    }
    :return: A statement with all redundant actions removed, IE: {
        'Action': ['s3:list*'], 'Effect': 'Allow', 'Resource': ['*']
    }
    """
    actions = statement.get("Action", [])

    if not isinstance(actions, list):
        actions = [actions]
    else:
        actions = sorted(set(actions))

    if "*" in actions:
        # Not sure if we should really be allowing this but
        #   if they've added a wildcard action there isn't any need to check what hits
        statement["Action"] = ["*"]
        return statement

    # Create a map of actions grouped by resource to prevent unnecessary checks
    resource_regex_map = defaultdict(list)
    for action in actions:
        # Represent the action as the regex lookup so this isn't being done on every iteration
        if "*" in action:
            resource_regex_map[action.split(":")[0]].append(action.replace("*", ".*"))

    async def _regex_check(action_str) -> str:
        # Check if the provided string hits on any other action for the same resource type
        # If not, return the string to be used as part of the reduced set of actions
        action_str_re = action_str.replace("*", ".*")
        action_resource = action_str.split(":")[0]

        resource_actions = resource_regex_map[action_resource]
        if not any(
            re.match(related_action, action_str_re, re.IGNORECASE)
            for related_action in resource_actions
            if related_action != action_str_re
        ):
            return action_str

    reduced_actions = await asyncio.gather(
        *[_regex_check(action_str) for action_str in actions]
    )
    statement["Action"] = [action.lower() for action in reduced_actions if action]

    return statement


async def normalize_statement(statement: dict) -> dict:
    """Refactors the statement dict and adds additional keys to be used for easy regex checks.

    :param statement: A statement, IE: {
        'Action': ['s3:listbucket', 's3:list*'], 'Effect': 'Allow', 'Resource': '*'
    }
    :return: A statement with all redundant actions removed, IE: {
        'Action': ['s3:listbucket', 's3:list*'],
        'ActionMap': {'s3': ['listbucket', 'list.*']},
        'Effect': 'Allow',
        'Resource': ['*']
        'ResourceAsRegex': ['.*']
    }
    """

    statement.pop("Sid", None)  # Drop the statement ID

    if "Resource" not in statement:
        # Currently, we only support Resource
        return statement
    elif not isinstance(statement["Resource"], list):
        # Ensure Resource is a list
        statement["Resource"] = [statement["Resource"]]

    if "*" in statement["Resource"] and len(statement["Resource"]) > 1:
        statement["Resource"] = ["*"]
    else:
        statement["Resource"].sort()

    # Add the regex repr of the resource to be used when comparing statements in a policy
    statement["ResourceAsRegex"] = [
        f"{statement.get('Effect')}:{resource}".replace("*", ".*")
        for resource in statement.get("Resource")
    ]

    statement = await reduce_statement_actions(statement)

    # Create a map of actions grouped by resource to prevent unnecessary checks
    statement["ActionMap"] = defaultdict(set)
    for action in statement["Action"]:
        # Represent the action as the regex lookup so this isn't being done on every iteration
        # if "*" in action:
        statement["ActionMap"][action.split(":")[0]].add(action.replace("*", ".*"))

    return statement


async def condense_statements(
    statements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Removes redundant policies, and actions that are already permitted by a different wildcard / partial wildcard
    statement.

    :param statements: A list of statements, IE: [
        {'Action': ['s3:listbucket'], 'Effect': 'Allow', 'Resource': ['*']},
        {'Action': ['s3:listbucket'], 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::bucket']},
        ...
    ]
    :return: A list of statements with all redundant policies removed, IE: [
        {'Action': ['s3:listbucket'], 'Effect': 'Allow', 'Resource': ['*']},
        ...
    ]
    """
    statements = await asyncio.gather(
        *[normalize_statement(statement) for statement in statements]
    )

    # statements.copy() so we don't mess up enumeration when popping statements with identical resource+effect
    # The offset variables are so we can access the correct element after elements have been removed
    pop_offset = 0
    for elem, statement in enumerate(statements.copy()):
        offset_elem = elem - pop_offset

        if (
            not statement.get("Action")
            or statement["Action"][0] == "*"
            or any(statement.get(se) for se in IGNORE_STATEMENTS_WITH)
        ):
            continue

        for inner_elem, inner_statement in enumerate(statements):
            if not (
                inner_statement.get("ResourceAsRegex")
                and statement.get("ResourceAsRegex")
            ):
                continue
            resource_match = await is_resource_match(
                inner_statement["ResourceAsRegex"], statement["ResourceAsRegex"]
            )
            action_match = await is_action_match(
                statement["ActionMap"], inner_statement["ActionMap"]
            )
            identical_resource = bool(
                statement["Resource"] == inner_statement["Resource"]
            )

            if offset_elem == inner_elem:
                continue
            elif statement["Effect"] != inner_statement["Effect"]:
                continue
            elif any(inner_statement.get(se) for se in IGNORE_STATEMENTS_WITH):
                continue
            elif not resource_match and not action_match:
                continue
            elif inner_statement.get("Condition"):
                continue
            elif (
                len(inner_statement["Action"]) == 1
                and inner_statement["Action"][0] == "*"
            ):
                continue

            if identical_resource:
                # The statements are identical so combine the actions
                statements[inner_elem]["Action"] = sorted(
                    list(set(statements[inner_elem]["Action"] + statement["Action"]))
                )
                for resource_type, perm_set in statement["ActionMap"].items():
                    for perm in perm_set:
                        statements[inner_elem]["ActionMap"][resource_type].add(perm)
            if action_match:
                # The statements are identical so combine the actions
                statements[inner_elem]["Resource"] = sorted(
                    list(
                        set(statements[inner_elem]["Resource"] + statement["Resource"])
                    )
                )

            if action_match or identical_resource:
                del statements[offset_elem]
                pop_offset += 1
                break

            action_pop_offset = 0
            # statement["Action"].copy() so we don't mess up enumerating Action when popping elements
            for action_elem, action in enumerate(statement["Action"].copy()):
                offset_action_elem = action_elem - action_pop_offset
                action_re = action.replace("*", ".*")
                action_resource = action.split(":")[0]
                resource_actions = inner_statement["ActionMap"][action_resource]

                if any(
                    re.match(related_action, action_re, re.IGNORECASE)
                    for related_action in resource_actions
                ):
                    # If the action falls under a different (inner) statement, remove it.
                    del statements[offset_elem]["Action"][offset_action_elem]
                    action_pop_offset += 1
                    statements[offset_elem]["ActionMap"][action_resource] = set(
                        act_re
                        for act_re in statements[offset_elem]["ActionMap"][
                            action_resource
                        ]
                        if act_re != action_re
                    )

    # Remove statements with no remaining actions and reduce actions once again to account for combined statements
    statements = await asyncio.gather(
        *[
            reduce_statement_actions(statement)
            for statement in statements
            if len(statement.get("Action", [])) > 0
            or any(statement.get(se) for se in IGNORE_STATEMENTS_WITH)
        ]
    )

    for elem in range(len(statements)):  # Remove eval keys
        statements[elem].pop("ActionMap", None)
        statements[elem].pop("ResourceAsRegex", None)

    return statements
