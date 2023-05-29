from common.models import PaginatedRequestQueryParams


def get_paginated_typeahead_response(
    response_data: list, query_params: PaginatedRequestQueryParams
) -> dict:
    response = {
        "data": response_data,
        "page": query_params.page,
        "page_size": query_params.page_size,
    }

    if len(response_data) == query_params.page_size:
        response["next_page"] = query_params.page + 1

    return response
