from typing import Any, TypedDict

from common.models import PaginatedRequestQueryParams


class TypeAheadResponse(TypedDict, total=False):
    data: list[Any]
    page: int
    page_size: int
    next_page: int


def get_paginated_typeahead_response(
    response_data: list, query_params: PaginatedRequestQueryParams
) -> TypeAheadResponse:
    response = {
        "data": response_data,
        "page": query_params.page,
        "page_size": query_params.page_size,
    }

    if len(response_data) == query_params.page_size:
        response["next_page"] = query_params.page or 0 + 1

    return TypeAheadResponse(**response)
