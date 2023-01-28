from sqlalchemy import desc
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import extract, operators
from sqlalchemy.sql.base import _entity_namespace_key
from sqlalchemy.util import to_list

DEFAULT_PAGE = 1
DEFAULT_SIZE = 20

OPERATOR_MAP = {
    "and": operators.and_,
    "or": operators.or_,
    "eq": operators.eq,
    "gt": operators.gt,
    "lte": operators.le,
    "lt": operators.lt,
    "le": operators.le,
    "gte": operators.ge,
    "ge": operators.ge,
    "ne": operators.ne,
    "not": operators.ne,
    "contains": operators.contains_op,
    "co": operators.contains_op,
    "in": operators.in_op,
    "exact": operators.eq,
    "iexact": operators.ilike_op,
    "startswith": operators.startswith_op,
    "sw": operators.startswith_op,
    "istartswith": lambda c, x: c.ilike(x.replace("%", "%%") + "%"),
    "iendswith": lambda c, x: c.ilike("%" + x.replace("%", "%%")),
    "endswith": operators.endswith_op,
    "ew": operators.endswith_op,
    "isnull": lambda c, x: x and c != None or c == None,  # noqa: E711, E712
    # 'range':        operators.between_op,
    "year": lambda c, x: extract("year", c) == x,
    "month": lambda c, x: extract("month", c) == x,
    "day": lambda c, x: extract("day", c) == x,
}


def paginate_query(query: Query, page: int = DEFAULT_PAGE, size: int = DEFAULT_SIZE):
    return query.offset((page - 1) * size).limit(size)


def determine_page_from_offset(offset: int, size: int = DEFAULT_SIZE):
    if size == 0:
        size = DEFAULT_SIZE
    return int(offset / size) + 1


def create_filter_from_url_params(
    query: Query,
    page: int = DEFAULT_PAGE,
    size: int = DEFAULT_SIZE,
    order_by: str = None,
    **kwargs
) -> Query:
    if size == 0:
        size = DEFAULT_SIZE
    from_entity = query._filter_by_zero()

    for arg, val in kwargs.items():
        val = to_list(val)
        split_arg = arg.split("__")
        namespace = _entity_namespace_key(
            from_entity, "".join(split_arg[:-1])
        )  # Right now join isn't really supported
        operation = split_arg[-1]
        if operation.startswith("~"):
            if "contains" in operation:
                query = query.filter(~namespace.contains(val))
            else:
                query = query.filter(~OPERATOR_MAP[operation[1:]](namespace, *val))
        else:
            if operation == "contains":
                query = query.filter(namespace.contains(val))
            else:
                query = query.filter(OPERATOR_MAP[operation](namespace, *val))

    query = paginate_query(query, page, size)

    if order_by and order_by.startswith("-"):
        query = query.order_by(desc(_entity_namespace_key(from_entity, order_by[1:])))
    elif order_by:
        query = query.order_by(_entity_namespace_key(from_entity, order_by))

    return query
