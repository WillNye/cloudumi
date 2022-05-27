from pynamodax.attributes import UnicodeAttribute

from common.lib.pynamo import NoqMapAttribute


class TagMap(NoqMapAttribute):
    Key = UnicodeAttribute()
    Value = UnicodeAttribute()
