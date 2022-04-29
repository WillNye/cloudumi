from unittest import TestCase

from asgiref.sync import async_to_sync

from common.lib.oidc import get_roles_from_token


class TestGetRolesFromToken(TestCase):
    def test_get_roles(self):
        test_roles = [
            "arn:aws:iam::350876197038:role/role_one",
            "arn:aws:iam::350876197038:role/role_two",
            "arn:aws:iam::350876197038:role/role_three",
        ]
        test_token = {
            "at_hash": "...",
            "sub": "...",
            "email_verified": True,
            "iss": "...",
            "cognito:username": "...",
            "custom:role_arns": ",".join(test_roles),
            "origin_jti": "...",
            "aud": "...",
            "event_id": "...",
            "token_use": "...",
            "auth_time": 1651094815,
            "exp": 1651098415,
            "iat": 1651094815,
            "jti": "...",
            "email": "test@noq.dev",
        }

        results = async_to_sync(get_roles_from_token)("cloudumidev_com", test_token)
        self.assertListEqual(sorted(list(results)), sorted(test_roles))
