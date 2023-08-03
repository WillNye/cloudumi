import math
from enum import Enum
from typing import Any, Optional, Type

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


async def filter_data(
    data, filter_obj, model: Optional[BaseModel] = None
) -> DataTableResponse:
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
                prop_val = item.get(token.propertyKey)
                if prop_val is None:  # If prop_val is None, do a generic search
                    generic_match = any(
                        token.value in str(item[key]) for key in item.keys()
                    )
                    match = match and generic_match
                else:
                    if token.operator == FilterOperator.equals:
                        match = match and prop_val == token.value
                    elif token.operator == FilterOperator.not_equals:
                        match = match and prop_val != token.value
                    elif token.operator == FilterOperator.contains:
                        match = match and (
                            prop_val is not None and token.value in prop_val
                        )
                    elif token.operator == FilterOperator.does_not_contain:
                        match = match and (
                            prop_val is None or token.value not in prop_val
                        )
                    elif token.operator == FilterOperator.greater_than:
                        match = match and prop_val > token.value
                    elif token.operator == FilterOperator.less_than:
                        match = match and prop_val < token.value
            if match:
                filtered_data.append(item)
        elif filter.operation == FilterOperation._or:
            match = False
            for token in filter.tokens:
                prop_val = item.get(token.propertyKey)
                if prop_val is None:  # If prop_val is None, do a generic search
                    generic_match = any(
                        token.value in str(item[key]) for key in item.keys()
                    )
                    match = match or generic_match
                else:
                    if token.operator == FilterOperator.equals:
                        match = match or prop_val == token.value
                    elif token.operator == FilterOperator.not_equals:
                        match = match or prop_val != token.value
                    elif token.operator == FilterOperator.contains:
                        match = match or (
                            prop_val is not None and token.value in prop_val
                        )
                    elif token.operator == FilterOperator.does_not_contain:
                        match = match or (
                            prop_val is None or token.value not in prop_val
                        )
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
        if model:
            paginated_data = [
                model.parse_obj(item).dict(by_alias=True)
                for item in filtered_data[start:end]
            ]
        else:
            paginated_data = filtered_data[start:end]
    else:
        if model:
            [model.parse_obj(item).dict(by_alias=True) for item in filtered_data]
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


def get_table_field_from_string(Table, field: str):
    nested_fields = str(field).split(".")
    if len(nested_fields) > 1:
        field = getattr(Table, nested_fields[0]).entity.class_
        if len(nested_fields) > 2:
            for sub_key in nested_fields[1:-1]:
                field = getattr(field, sub_key).entity.class_
        field = getattr(field, nested_fields[-1])

    return field


async def get_query_conditions(Table, token, conditions):
    if isinstance(token.propertyKey, str):
        filter_key = getattr(Table, token.propertyKey)
    else:
        filter_key = token.propertyKey

    if token.operator == FilterOperator.equals:
        conditions.append(filter_key == token.value)
    elif token.operator == FilterOperator.not_equals:
        conditions.append(filter_key != token.value)
    elif token.operator == FilterOperator.contains:
        conditions.append(filter_key.ilike(f"%{token.value}%"))
    elif token.operator == FilterOperator.does_not_contain:
        conditions.append(filter_key.notilike(f"%{token.value}%"))
    elif token.operator == FilterOperator.greater_than:
        conditions.append(filter_key > token.value)
    elif token.operator == FilterOperator.less_than:
        conditions.append(filter_key < token.value)
    return conditions


async def filter_data_with_sqlalchemy(
    filter_obj: dict, tenant: Tenant, Table: Type[Base], allow_deleted: bool = False
):
    options = FilterModel.parse_obj(filter_obj)
    filter = options.filtering
    sorting = options.sorting
    pagination = options.pagination
    conditions = []

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            query = select(Table).filter(getattr(Table, "tenant") == tenant)
            conditions = []
            if not allow_deleted:
                query = query.filter(getattr(Table, "deleted") == allow_deleted)
            if filter and filter.tokens:
                if filter.operation == FilterOperation._and:
                    for token in filter.tokens:
                        try:
                            token.propertyKey = get_table_field_from_string(Table, token.propertyKey)
                        except AttributeError:
                            return []
                        conditions = await get_query_conditions(
                            Table, token, conditions
                        )
                        query = query.filter(and_(*conditions))
                elif filter.operation == FilterOperation._or:
                    for token in filter.tokens:
                        try:
                            token.propertyKey = get_table_field_from_string(Table, token.propertyKey)
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

            filtered_count_query = query.with_only_columns(func.count()).order_by(None)
            filtered_count = await session.execute(filtered_count_query)
            filtered_count = filtered_count.scalar()
            pages = math.ceil(filtered_count / pagination.pageSize)

            if pagination and pagination.pageSize and pagination.currentPageIndex:
                query = query.offset(
                    (pagination.currentPageIndex - 1) * pagination.pageSize
                ).limit(pagination.pageSize)
            res = await session.execute(query)

            return PaginatedQueryResponse(
                filtered_count=filtered_count,
                pages=pages,
                page_size=pagination.pageSize,
                current_page_index=pagination.currentPageIndex,
                data=res.unique().scalars().all(),
            )


async def enrich_sqlalchemy_stmt_with_filter_obj(
    filter_obj: FilterModel, sql_model: Type[Base], sql_stmt: select
) -> select:
    filter = filter_obj.filtering
    sorting = filter_obj.sorting
    pagination = filter_obj.pagination
    conditions = []

    if filter and filter.tokens:
        for token in filter.tokens:
            try:
                token.propertyKey = get_table_field_from_string(sql_model, token.propertyKey)
            except AttributeError:
                return []
            conditions = await get_query_conditions(sql_model, token, conditions)

        if conditions and filter.operation == FilterOperation._and:
            sql_stmt = sql_stmt.filter(and_(*conditions))
        elif conditions and filter.operation == FilterOperation._or:
            sql_stmt = sql_stmt.filter(or_(*conditions))
        elif conditions:
            raise AttributeError(f"Unsupported filter operation: {filter.operation}")

    if sorting and sorting.sortingColumn:
        sort_field = get_table_field_from_string(
            sql_model, sorting.sortingColumn.sortingField
        )
        sql_stmt = sql_stmt.order_by(
            sort_field.desc() if sorting.sortingDescending else sort_field.asc()
        )

    if pagination and pagination.pageSize and pagination.currentPageIndex:
        sql_stmt = sql_stmt.limit(pagination.pageSize).offset(
            (pagination.currentPageIndex - 1) * pagination.pageSize
        )

    return sql_stmt


async def generate_paginated_response(sql_stmt):
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            filtered_count_query = (
                sql_stmt.with_only_columns(func.count())
                .order_by(None)
                .offset(None)
                .limit(None)
            )
            filtered_count = await session.execute(filtered_count_query)
            filtered_count = filtered_count.scalar()
            pages = math.ceil(filtered_count / sql_stmt._limit)

            res = await session.execute(sql_stmt)
            return PaginatedQueryResponse(
                filtered_count=filtered_count,
                pages=pages,
                page_size=sql_stmt._limit,
                current_page_index=sql_stmt._offset,
                data=res.unique().scalars().all(),
            )
