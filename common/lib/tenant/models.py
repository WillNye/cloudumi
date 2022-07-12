from enum import Enum

from pynamodax.attributes import BooleanAttribute, NumberAttribute, UnicodeAttribute
from pynamodax.indexes import AllProjection, GlobalSecondaryIndex

from common.config import config
from common.config.config import get_logger
from common.lib.plugins import get_plugin_by_name
from common.lib.pynamo import GlobalNoqModel, NoqMapAttribute

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = get_logger(__name__)


class MembershipTier(Enum):
    FREE = 0
    UNLIMITED = 999

    @classmethod
    def values(cls):
        return [str(mt.value) for mt in list(cls)]


class MembershipTierAttribute(UnicodeAttribute):
    def serialize(self, value: any) -> any:
        if isinstance(value, MembershipTier):
            return value.value

        try:
            return MembershipTier(value).value
        except ValueError:
            raise ValueError(
                f"membership_tier must be one of {', '.join(MembershipTier.values())}"
            )


class ClusterShardingIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = "cluster-sharding-index"
        read_capacity_units = 5
        write_capacity_units = 1
        projection = AllProjection()
        region = config.region

    noq_cluster = UnicodeAttribute(hash_key=True)


class TenantDetails(GlobalNoqModel):
    class Meta:
        table_name = "tenant_details"  # This table is global across all clusters in an environment
        region = config.region

    name = UnicodeAttribute(hash_key=True)
    membership_tier = MembershipTierAttribute()
    is_active = BooleanAttribute(default=True)
    created_by = UnicodeAttribute()
    created_at = NumberAttribute()
    eula_info = NoqMapAttribute(null=True)
    noq_cluster = UnicodeAttribute()
    license_expiration = NumberAttribute(null=True)

    cluster_sharding_index = ClusterShardingIndex()
