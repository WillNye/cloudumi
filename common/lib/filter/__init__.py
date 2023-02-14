import math
from enum import Enum
from typing import Any, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.group_memberships.models import GroupMembership  # noqa: F401, E402
from common.groups.models import Group  # noqa: F401, E402
from common.lib.pydantic import BaseModel
from common.models import DataTableResponse
from common.pg_core.models import Base  # noqa: F401,E402
from common.tenants.models import Tenant  # noqa: F401, E402
from common.users.models import User  # noqa: F401, E402


class PaginatedQueryResponse(BaseModel):
    filtered_count: int
    pages: int
    page_size: int
    current_page_index: int
    data: list[Any]


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
    does_not_contain = "!:"
    greater_than = ">"
    less_than = "<"


class FilterToken(BaseModel):
    propertyKey: Optional[str]
    operator: FilterOperator
    value: Any


class FilterOperation(Enum):
    _and = "and"
    _or = "or"


class Filter(BaseModel):
    tokens: list[FilterToken] = []
    operation: FilterOperation = FilterOperation._and


class FilterModel(BaseModel):
    pagination: FilterPagination = FilterPagination()
    sorting: Optional[FilterSorting]
    filtering: Filter = None


async def filter_data(data, filter_obj) -> DataTableResponse:
    options = FilterModel.parse_obj(filter_obj)
    filter = options.filtering
    sorting = options.sorting
    pagination = options.pagination
    filtered_data = []
    total_count = len(data)
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
                    match = match and token.value in prop_val
                elif token.operator == FilterOperator.does_not_contain:
                    match = match and token.value not in prop_val
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
                    match = match or token.value in prop_val
                elif token.operator == FilterOperator.does_not_contain:
                    match = match or token.value not in prop_val
                elif token.operator == FilterOperator.greater_than:
                    match = match or prop_val > token.value
                elif token.operator == FilterOperator.less_than:
                    match = match or prop_val < token.value
            if match:
                filtered_data.append(item)
    filtered_count = len(filtered_data)
    if sorting and sorting.sortingColumn:
        filtered_data.sort(
            key=lambda x: x[sorting.sortingColumn.sortingField],
            reverse=sorting.sortingDescending,
        )
    if pagination and pagination.pageSize and pagination.currentPageIndex:
        start = (pagination.currentPageIndex - 1) * pagination.pageSize
        end = start + pagination.pageSize
        paginated_data = filtered_data[start:end]
    else:
        paginated_data = filtered_data

    return DataTableResponse(
        totalCount=total_count, filteredCount=filtered_count, data=paginated_data
    )


async def get_relationship_tables(Table) -> list[str]:
    relationship_tables = []
    for relationship in Table.__mapper__.relationships:
        relationship_tables.append(relationship.key)
    return relationship_tables


async def get_dynamic_objects_from_filter_tokens(Table, token):
    """
    This function get_dynamic_objects_from_filter_tokens takes in a Table and a token and returns the token with updated values if necessary.

    It's a necessary evil because of the way the `filter_data_with_sqlalchemy` gets into meta programming to build filters.
    We have to resolve the relationship objects and since all pointers are lazily loaded, we have to actually import the
    relevant model to get the object.

    The function first retrieves related tables from the input Table using the get_relationship_tables function. Then, it splits the
    value of the token's propertyKey into separate components and processes them accordingly. If the components contain more than one item,
    the function attempts to import the relevant module and table based on the first component. If a matching module and table are found,
    the token's propertyKey and value are updated accordingly.

    If the token's value could not be found in the related table, an AttributeError will be raised.

    :param Table: The input Table object.
    :type Table: object
    :param token: The input token object.
    :type token: object
    :return: The updated token object.
    :rtype: object
    """
    original_token_value = token.value
    rel_tables = await get_relationship_tables(Table)
    propertyKey_tokens = str(token.propertyKey).split(".")
    if len(propertyKey_tokens) > 1:
        import importlib

        rel_name_wo_ess = propertyKey_tokens[0].lower()
        rel_name_w_ess = (propertyKey_tokens[0] + "s").lower()
        value_attribute = propertyKey_tokens[1]
        if rel_name_w_ess in rel_tables or rel_name_wo_ess in rel_tables:
            try:
                propertyKeyModule = importlib.import_module(
                    f"common.{rel_name_wo_ess}.models"
                )
            except ImportError:
                try:
                    propertyKeyModule = importlib.import_module(
                        f"common.{rel_name_w_ess}.models"
                    )
                except ImportError:
                    raise
            try:
                propertyKeyTable = getattr(
                    propertyKeyModule, rel_name_wo_ess.capitalize()
                )
            except AttributeError:
                try:
                    propertyKeyTable = getattr(
                        propertyKeyModule, rel_name_w_ess.capitalize()
                    )
                except AttributeError:
                    raise
            if rel_name_w_ess in rel_tables:
                token.propertyKey = rel_name_w_ess
            elif rel_name_wo_ess in rel_tables:
                token.propertyKey = rel_name_wo_ess
            else:
                raise AttributeError(
                    f"Could not find {rel_name_w_ess} or {rel_name_wo_ess} in relationships: {rel_tables}"
                )
            token.value = await propertyKeyTable.get_by_attr(
                value_attribute, token.value
            )
            if token.value is None:
                raise AttributeError(
                    f"Could not find {value_attribute} with value {original_token_value} in {propertyKeyTable}"
                )
    return token


async def get_query_conditions(Table, token, conditions):
    if token.operator == FilterOperator.equals:
        conditions.append(getattr(Table, token.propertyKey) == token.value)
    elif token.operator == FilterOperator.not_equals:
        conditions.append(getattr(Table, token.propertyKey) != token.value)
    elif token.operator == FilterOperator.contains:
        conditions.append(getattr(Table, token.propertyKey).ilike(f"%{token.value}%"))
    elif token.operator == FilterOperator.does_not_contain:
        conditions.append(
            getattr(Table, token.propertyKey).notilike(f"%{token.value}%")
        )
    elif token.operator == FilterOperator.greater_than:
        conditions.append(getattr(Table, token.propertyKey) > token.value)
    elif token.operator == FilterOperator.less_than:
        conditions.append(getattr(Table, token.propertyKey) < token.value)
    return conditions


async def filter_data_with_sqlalchemy(filter_obj, tenant, Table):
    options = FilterModel.parse_obj(filter_obj)
    filter = options.filtering
    sorting = options.sorting
    pagination = options.pagination

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            query = select(Table)
            conditions = [getattr(Table, "tenant") == tenant]
            if filter and filter.tokens:
                if filter.operation == FilterOperation._and:
                    for token in filter.tokens:
                        try:
                            token = await get_dynamic_objects_from_filter_tokens(
                                Table, token
                            )
                        except AttributeError:
                            return []
                        conditions = await get_query_conditions(
                            Table, token, conditions
                        )
                        query = query.filter(and_(*conditions))
                elif filter.operation == FilterOperation._or:
                    conditions = []
                    for token in filter.tokens:
                        try:
                            token = await get_dynamic_objects_from_filter_tokens(
                                Table, token
                            )
                        except AttributeError:
                            return []
                        conditions = await get_query_conditions(
                            Table, token, conditions
                        )
                    query = query.filter(
                        and_(or_(*conditions), [getattr(Table, "tenant") == tenant])
                    )

            if sorting and sorting.sortingColumn:
                query = query.order_by(
                    getattr(Table, sorting.sortingColumn.sortingField).desc()
                    if sorting.sortingDescending
                    else getattr(Table, sorting.sortingColumn.sortingField).asc()
                )

            if pagination and pagination.pageSize and pagination.currentPageIndex:
                query = query.offset(
                    (pagination.currentPageIndex - 1) * pagination.pageSize
                ).limit(pagination.pageSize)
            res = await session.execute(query)

            filtered_count_query = query.with_only_columns(func.count()).order_by(None)
            filtered_count = await session.execute(filtered_count_query)
            filtered_count = filtered_count.scalar()
            pages = math.ceil(filtered_count / pagination.pageSize)
            return PaginatedQueryResponse(
                filtered_count=filtered_count,
                pages=pages,
                page_size=pagination.pageSize,
                current_page_index=pagination.currentPageIndex,
                data=res.unique().scalars().all(),
            )
