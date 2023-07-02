from typing import Any, Dict, List

import ujson as json

from common.config import config
from common.models import WebResponse

log = config.get_logger(__name__)


async def handle_generic_error_response(
    request,
    message: str,
    errors: List[str],
    status_code: int,
    reason: str,
    log_data: Dict[str, Any],
) -> bool:
    """

    Args:
        request: Tornado web request
        message: Message to be logged
        reason: One line reason for the response (easier for frontend to parse)
        errors: List of errors to be logged, and to be returned to user
        status_code: Status code to return to end-user
        log_data: Dictionary of data to log, typically containing function and information about the user.

    Returns:
        boolean

    """
    log.error({**log_data, "message": message, "errors": errors})
    res = WebResponse(
        status="error",
        status_code=status_code,
        errors=errors,
        reason=reason,
        message=message,
    )
    request.set_status(status_code)
    request.write(json.loads(res.json(exclude_unset=True)))
    await request.finish()
    return True
