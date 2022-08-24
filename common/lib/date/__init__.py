import datetime
from typing import Union

import dateparser


def parse_date_string(d: Union[str, datetime.datetime]) -> datetime.datetime:
    dt = None
    if isinstance(d, datetime.date):
        dt = datetime.datetime.combine(d, datetime.datetime.min.time())
    if isinstance(d, datetime.datetime):
        dt = d
    if isinstance(d, str):
        dt = dateparser.parse(d)
    if dt:
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    raise Exception(f"Unable to parse date: {d}")
