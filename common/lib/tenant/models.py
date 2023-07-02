from datetime import datetime
from enum import Enum

from pynamodax.attributes import BooleanAttribute, NumberAttribute, UnicodeAttribute
from pynamodax.indexes import AllProjection, GlobalSecondaryIndex

from common.config import config
from common.config.config import get_logger
from common.lib.plugins import get_plugin_by_name
from common.lib.pynamo import GlobalNoqModel, NoqListAttribute, NoqMapAttribute

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = get_logger(__name__)


class MembershipTier(Enum):
    FREE = 0
    UNLIMITED = -1

    @classmethod
    def values(cls):
        return [str(mt.value) for mt in list(cls)]


class MembershipTierAttribute(NumberAttribute):
    def serialize(self, value: any) -> any:
        if isinstance(value, MembershipTier):
            return super(MembershipTierAttribute, self).serialize(value.value)

        try:
            return super(MembershipTierAttribute, self).serialize(
                MembershipTier(value).value
            )
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


class AWSMarketplaceTenantDetails(GlobalNoqModel):
    class Meta:
        table_name = "aws_marketplace_tenant_details"  # This table is global across all clusters in an environment
        region = (
            config.get("_global_.accounts.aws_marketplace_tenant_details.region")
            or config.region
        )

    customer_identifier = UnicodeAttribute(hash_key=True)
    customer_account_id = UnicodeAttribute(null=True)
    is_free_trial_term_present = BooleanAttribute(default=False)
    subscription_action = UnicodeAttribute(null=True)
    subscription_expired = BooleanAttribute(default=False)
    successfully_subscribed = BooleanAttribute(default=False)
    product_code = UnicodeAttribute(null=True)
    registration_token = UnicodeAttribute(null=True)
    created_at = NumberAttribute()
    updated_at = NumberAttribute()
    change_history = NoqListAttribute(null=True)
    company_name = UnicodeAttribute(null=True)
    contact_person_first_name = UnicodeAttribute(null=True)
    contact_person_last_name = UnicodeAttribute(null=True)
    contact_person = UnicodeAttribute(null=True)
    contact_phone = UnicodeAttribute(null=True)
    contact_email = UnicodeAttribute(null=True)
    domain = UnicodeAttribute(null=True)

    @classmethod
    async def customer_id_exists(cls, customer_identifier: str) -> bool:
        results = await cls.query(customer_identifier, limit=1)
        try:
            return bool(results.next())
        except StopIteration:
            return False

    @classmethod
    async def create(
        cls,
        customer_identifier: str,
        registration_token: str = "",
        product_code: str = "",
        customer_account_id: str = "",
    ) -> "AWSMarketplaceTenantDetails":
        aws_marketplace_details = cls(
            customer_identifier=customer_identifier,
            customer_account_id=customer_account_id,
            registration_token=registration_token,
            product_code=product_code,
            created_at=int((datetime.utcnow()).timestamp()),
            updated_at=int((datetime.utcnow()).timestamp()),
        )
        await aws_marketplace_details.save()
        return aws_marketplace_details

    @classmethod
    async def update_subscription(cls, message: dict) -> bool:
        try:
            customer_identifier = message["customer-identifier"]
            tenant = await cls.get(customer_identifier)

            action = message["action"]

            if action == "subscribe-success":
                tenant.successfully_subscribed = True
                tenant.subscription_action = "subscribe-success"
            elif action == "subscribe-fail":
                tenant.successfully_subscribed = False
                tenant.subscription_action = "subscribe-fail"
            elif action == "unsubscribe-pending":
                tenant.subscription_expired = True
                tenant.subscription_action = "unsubscribe-pending"
            elif action == "unsubscribe-success":
                tenant.subscription_expired = True
                tenant.subscription_action = "unsubscribe-success"

            tenant.is_free_trial_term_present = message.get(
                "isFreeTrialTermPresent", False
            )
            tenant.product_code = message.get("product-code")
            tenant.updated_at = int((datetime.utcnow()).timestamp())

            if tenant.change_history:
                tenant.change_history.append({str(datetime.utcnow()): action})
            else:
                tenant.change_history = [{str(datetime.utcnow()): action}]

            await tenant.save()
            return True
        except Exception as e:
            log.exception({"error": f"Error updating tenant details: {str(e)}"})
            return False


class TenantDetails(GlobalNoqModel):
    class Meta:
        table_name = "tenant_details"  # This table is global across all clusters in an environment
        region = config.get("_global_.accounts.tenant_data.region") or config.region

    name = UnicodeAttribute(hash_key=True)
    membership_tier = MembershipTierAttribute()
    is_active = BooleanAttribute(default=True)
    created_by = UnicodeAttribute()
    created_at = NumberAttribute()
    eula_info = NoqMapAttribute(null=True)
    noq_cluster = UnicodeAttribute()
    license_expiration = NumberAttribute(null=True)
    notes = UnicodeAttribute(null=True)

    cluster_sharding_index = ClusterShardingIndex()

    async def submit_default_eula(self, signed_by: str, ip_address: str):
        from common.lib.tenant.utils import get_current_eula_version

        self.eula_info = {
            "signed_at": int((datetime.utcnow()).timestamp()),
            "version": await get_current_eula_version(),
            "signed_by": {"email": signed_by, "ip_address": ip_address},
        }

        await self.save()

    @classmethod
    async def tenant_exists(cls, tenant_name: str) -> bool:
        results = await cls.query(tenant_name, limit=1)
        try:
            return bool(results.next())
        except StopIteration:
            return False

    @staticmethod
    async def _get_cluster() -> str:
        """
        TODO: Proper tenant assignment.
        Scope defined in https://perimy.atlassian.net/browse/EN-887
        """
        return config.get("_global_.deployment.cluster_id")

    @classmethod
    async def create(
        cls,
        name: str,
        created_by: str,
        membership_tier: int = MembershipTier.UNLIMITED.value,
        eula_info: dict = None,
        notes: str = None,
        noq_cluster: str = None,
    ) -> "TenantDetails":
        # How to calculate license_expiration?
        if noq_cluster:
            # TODO: Validate it exists
            pass
        else:
            noq_cluster = await cls._get_cluster()

        tenant_details = cls(
            name=name,
            created_by=created_by,
            membership_tier=membership_tier,
            eula_info=eula_info,
            notes=notes,
            created_at=int((datetime.utcnow()).timestamp()),
            noq_cluster=noq_cluster,
        )
        await tenant_details.save()
        return tenant_details
