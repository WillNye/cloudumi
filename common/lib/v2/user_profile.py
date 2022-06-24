from typing import Dict, List

from common.config import config


async def get_custom_page_header(
    user: str, user_groups: List[str], tenant: str
) -> Dict[str, str]:
    """
    Args:
        user: The user's e-mail address
        user_groups: the user's group memberships

    Returns:
        Headers to show on the page. These headers can be specific to the user's group memberships, or the user's
        email address, or generic. If a configuration is not set, a header will not be shown.

    Example:
        Visit https://YOUR_CONSOLEME_DOMAIN/config
        Add this to the page:
        ```
        custom_headers_for_group_members:
          - users_or_groups:
             - you@example.com
             - a_group@example.com
            title: Important message!
            message: Read this!
        ```
    """
    if config.get_tenant_specific_key(
        "example_config.is_example_config", tenant, False
    ):
        return {
            "custom_header_message_title": config.get_tenant_specific_key(
                "example_config.title", tenant
            ),
            "custom_header_message_text": config.get_tenant_specific_key(
                "example_config.text", tenant
            ),
            "custom_header_message_route": config.get_tenant_specific_key(
                "example_config.routes", tenant
            ),
        }
    custom_headers_for_group_members = config.get_tenant_specific_key(
        "dynamic_config.custom_headers_for_group_members", tenant, []
    )
    for custom_header in custom_headers_for_group_members:
        for header_group in custom_header.get("users_or_groups", []):
            if header_group in user_groups or user == header_group:
                return {
                    "custom_header_message_title": custom_header.get("title", ""),
                    "custom_header_message_text": custom_header.get("message", ""),
                    "custom_header_message_route": custom_header.get("route", ".*"),
                }
    return {
        "custom_header_message_title": config.get_tenant_specific_key(
            "headers.custom_header_message.title", tenant, ""
        ),
        "custom_header_message_text": config.get_tenant_specific_key(
            "headers.custom_header_message.text", tenant, ""
        ),
        "custom_header_message_route": config.get_tenant_specific_key(
            "headers.custom_header_message.route", tenant, ".*"
        ),
    }
