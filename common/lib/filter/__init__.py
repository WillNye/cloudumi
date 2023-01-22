# Data filter for tables using CloudScape Property Filter
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.group_memberships.models import GroupMembership  # noqa: F401, E402
from common.groups.models import Group  # noqa: F401, E402
from common.lib.pydantic import BaseModel
from common.models import DataTableResponse
from common.pg_core.models import Base  # noqa: F401,E402
from common.users.models import User  # noqa: F401, E402


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
    value: int | date | datetime | float | str


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
                        if token.operator == FilterOperator.equals:
                            conditions.append(
                                getattr(Table, token.propertyKey) == token.value
                            )
                        elif token.operator == FilterOperator.not_equals:
                            conditions.append(
                                getattr(Table, token.propertyKey) != token.value
                            )
                        elif token.operator == FilterOperator.contains:
                            conditions.append(
                                getattr(Table, token.propertyKey).ilike(
                                    f"%{token.value}%"
                                )
                            )
                        elif token.operator == FilterOperator.greater_than:
                            conditions.append(
                                getattr(Table, token.propertyKey) > token.value
                            )
                        elif token.operator == FilterOperator.less_than:
                            conditions.append(
                                getattr(Table, token.propertyKey) < token.value
                            )
                    query = query.filter(and_(*conditions))
                elif filter.operation == FilterOperation._or:
                    conditions = []
                    for token in filter.tokens:
                        if token.operator == FilterOperator.equals:
                            conditions.append(
                                getattr(Table, token.propertyKey) == token.value
                            )
                        elif token.operator == FilterOperator.not_equals:
                            conditions.append(
                                getattr(Table, token.propertyKey) != token.value
                            )
                        elif token.operator == FilterOperator.contains:
                            conditions.append(
                                getattr(Table, token.propertyKey).ilike(
                                    f"%{token.value}%"
                                )
                            )
                        elif token.operator == FilterOperator.greater_than:
                            conditions.append(
                                getattr(Table, token.propertyKey) > token.value
                            )
                        elif token.operator == FilterOperator.less_than:
                            conditions.append(
                                getattr(Table, token.propertyKey) < token.value
                            )
                    query = query.filter(or_(*conditions))

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
            return res.scalars().all()
