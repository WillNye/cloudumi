import asyncio
import json
from datetime import datetime

import sqlalchemy.exc

from common.aws.role_access.models import AWSRoleAccess, RoleAccessTypes
from common.config.globals import ASYNC_PG_SESSION
from common.identity.models import AwsIdentityRole
from common.tenants.models import Tenant
from common.users.models import User
from functional_tests.conftest import TEST_USER_DOMAIN_US, FunctionalTest


async def setup_db():
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            tenant = await Tenant.get_by_name(TEST_USER_DOMAIN_US)
            if not tenant:
                tenant = await Tenant.create(
                    name=TEST_USER_DOMAIN_US, organization_id=TEST_USER_DOMAIN_US
                )
            try:
                await AwsIdentityRole.create(
                    tenant,
                    "test_role_access",
                    "arn:aws:iam::123456789012:role/test_role_access",
                )
            except sqlalchemy.exc.IntegrityError:
                pass
            identity_role = await AwsIdentityRole.get_by_role_arn(
                tenant, "arn:aws:iam::123456789012:role/test_role_access"
            )
            try:
                await User.create(
                    tenant, "test_role_access", "test_role_access@noq.dev", "password"
                )
            except sqlalchemy.exc.IntegrityError:
                pass
            user = await User.get_by_email(tenant, "test_role_access@noq.dev")
            try:
                await AWSRoleAccess.create(
                    tenant,
                    RoleAccessTypes.credential_access,
                    identity_role,
                    False,
                    datetime.now(),
                    user=user,
                )
            except sqlalchemy.exc.IntegrityError:
                pass


async def teardown_db():
    tenant = await Tenant.get_by_name(TEST_USER_DOMAIN_US)
    role_access = await AWSRoleAccess.get_by_arn(
        tenant, "arn:aws:iam::123456789012:role/test_role_access"
    )
    user = await User.get_by_email(tenant, "test_role_access@noq.dev")
    identity_role = await AwsIdentityRole.get_by_role_arn(
        tenant, "arn:aws:iam::123456789012:role/test_role_access"
    )

    try:
        await role_access.delete()
    except sqlalchemy.exc.IntegrityError:
        pass
    try:
        await user.delete()
    except sqlalchemy.exc.IntegrityError:
        pass
    try:
        await identity_role.delete()
    except sqlalchemy.exc.IntegrityError:
        pass
    try:
        await tenant.delete()
    except sqlalchemy.exc.IntegrityError:
        pass


class TestAPIV4RoleAccess(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        asyncio.run(setup_db())

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        asyncio.run(teardown_db())

    def test_retrieve_items(self):
        res = self.make_request("/api/v4/roles/access", method="post", body={})
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertIn("data", res_j.keys())
        data = res_j.get("data")
        self.assertIn("access_roles", data.keys())
        access_roles = data.get("access_roles")
        self.assertGreater(len(access_roles), 0)

    def test_filter_retrieve_items(self):
        body = {
            "filter": {
                "pagination": {"currentPageIndex": 1, "pageSize": 30},
                "sorting": {
                    "sortingColumn": {
                        "id": "id",
                        "sortingField": "id",
                        "header": "id",
                        "minWidth": 180,
                    },
                    "sortingDescending": False,
                },
                "filtering": {
                    "tokens": [
                        {
                            "propertyKey": "user.email",
                            "operator": "=",
                            "value": "test_role_access@noq.dev",
                        }
                    ],
                    "operation": "and",
                },
            }
        }

        res = self.make_request("/api/v4/roles/access", method="post", body=body)
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertIn("data", res_j.keys())
        data = res_j.get("data")
        self.assertIn("access_roles", data.keys())
        access_roles = data.get("access_roles")
        self.assertGreater(len(access_roles), 0)

    def test_filter_not_found_returns_500(self):
        body = {
            "filter": {
                "pagination": {"currentPageIndex": 1, "pageSize": 30},
                "sorting": {
                    "sortingColumn": {
                        "id": "id",
                        "sortingField": "id",
                        "header": "id",
                        "minWidth": 180,
                    },
                    "sortingDescending": False,
                },
                "filtering": {
                    "tokens": [
                        {
                            "propertyKey": "user.email",
                            "operator": "=",
                            "value": "not_exists@noq.dev",
                        }
                    ],
                    "operation": "and",
                },
            }
        }

        res = self.make_request("/api/v4/roles/access", method="post", body=body)
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertIn("data", res_j.keys())
        data = res_j.get("data")
        self.assertIn("access_roles", data.keys())
        access_roles = data.get("access_roles")
        self.assertEqual(len(access_roles), 0)
