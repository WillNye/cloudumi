# Data filter for tables using CloudScape Property Filter

from enum import Enum
from typing import Optional

from common.lib.pydantic import BaseModel


class FilterPagination(BaseModel):
    currentPageIndex: int = 1
    pageSize: int = 30


class FilterSortingColumn(BaseModel):
    id: str
    sortingField: str
    header: str
    minWidth: int


class FilterSorting(BaseModel):
    sortingColumn: FilterSortingColumn
    sortingDescending: bool = False


class FilterOperator(Enum):
    equals = "="
    not_equals = "!="
    contains = ":"
    greater_than = ">"
    less_than = "<"


class FilterToken(BaseModel):
    propertyKey: Optional[str]
    operator: FilterOperator
    value: int | float | str


class FilterOperation(Enum):
    _and = "and"
    _or = "or"


class Filter(BaseModel):
    tokens: list[FilterToken] = []
    operation: FilterOperation = FilterOperation._and


class FilterModel(BaseModel):
    pagination: FilterPagination
    sorting: FilterSorting
    filtering: Filter = None


# async def filter_data(data, filter, page_size=None, current_page_index=None, sorting_column=None, sorting_descending=False)
async def filter_data(data, filter_obj):
    options = FilterModel.parse_obj(filter_obj)
    filter = options.filtering
    sorting = options.sorting
    pagination = options.pagination
    filtered_data = []
    for item in data:
        if not filter or not filter.tokens:
            filtered_data.append(item)
            continue
        if filter.operation == FilterOperation._and:
            match = True
            for token in filter.tokens:
                prop_val = item[token.propertyKey]
                if token.operator == FilterOperator.equals:
                    match = match and prop_val == token.value
                elif token.operator == FilterOperator.not_equals:
                    match = match and prop_val != token.value
                elif token.operator == FilterOperator.contains:
                    match = match and prop_val in token.value
                elif token.operator == FilterOperator.greater_than:
                    match = match and prop_val > token.value
                elif token.operator == FilterOperator.less_than:
                    match = match and prop_val < token.value
            if match:
                filtered_data.append(item)
        elif filter.operation == FilterOperation._or:
            match = False
            for token in filter.tokens:
                prop_val = item[token.propertyKey]
                if token.operator == FilterOperator.equals:
                    match = match or prop_val == token.value
                elif token.operator == FilterOperator.not_equals:
                    match = match or prop_val != token.value
                elif token.operator == FilterOperator.contains:
                    match = match or prop_val in token.value
                elif token.operator == FilterOperator.greater_than:
                    match = match or prop_val > token.value
                elif token.operator == FilterOperator.less_than:
                    match = match or prop_val < token.value
            if match:
                filtered_data.append(item)
    if sorting.sortingColumn:
        filtered_data.sort(
            key=lambda x: x[sorting.sortingColumn.sortingField],
            reverse=sorting.sortingDescending,
        )
    if pagination.pageSize and pagination.currentPageIndex:
        start = (pagination.currentPageIndex - 1) * pagination.pageSize
        end = start + pagination.pageSize
        paginated_data = filtered_data[start:end]
    else:
        paginated_data = filtered_data
    return paginated_data
