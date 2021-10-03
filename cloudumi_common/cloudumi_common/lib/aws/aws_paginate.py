import functools


def aws_paginated(
    response_key,
    request_pagination_marker="Marker",
    response_pagination_marker="Marker",
):
    def decorator(func):
        @functools.wraps(func)
        def decorated_function(*args, **kwargs):
            results = []

            while True:
                response = func(*args, **kwargs)
                results.extend(response[response_key])

                # If the "next" pagination marker is in the response, then paginate. Responses may not always have
                # items in the response_key, so we should only key off of the response_pagination_marker.
                if response.get(response_pagination_marker):
                    kwargs.update(
                        {
                            request_pagination_marker: response[
                                response_pagination_marker
                            ]
                        }
                    )
                else:
                    break
            return results

        return decorated_function

    return decorator
