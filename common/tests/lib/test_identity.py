import pytest

from common.lib.cognito.identity import CognitoUserClient


@pytest.mark.parametrize(
    "username,secret_code,tenant,expected",
    [
        (
            "user",
            "381039",
            "example.noq.dev",
            "otpauth://totp/example.noq.dev:user?secret=381039&issuer=example.noq.dev",
        ),
    ],
)
def test_get_totp_uri(username, secret_code, tenant, expected):
    uri = CognitoUserClient.get_totp_uri(username, secret_code, tenant)
    assert uri == expected
