import asyncio
import os

from locust import FastHttpUser, run_single_user, task

from common.lib.jwt import generate_jwt_token

TEST_USER_NAME = "user@noq.dev"
TEST_USER_GROUPS = ["engineering@noq.dev"]

TEST_USER_DOMAIN: str = os.getenv("TEST_USER_DOMAIN")

stage = os.getenv("STAGE", "staging")
if not TEST_USER_DOMAIN:
    if stage == "staging":
        TEST_USER_DOMAIN = "corp.staging.noq.dev"
    if stage == "prod":
        TEST_USER_DOMAIN = "corp.noq.dev"
    if stage == "dev":
        TEST_USER_DOMAIN = "localhost"
TEST_USER_DOMAIN_US = (
    TEST_USER_DOMAIN.replace(".", "_").replace("https://", "").split(":")[0]
)


class LoadTest(FastHttpUser):
    host = f"{TEST_USER_DOMAIN}"
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
    }

    token = asyncio.run(
        generate_jwt_token(
            TEST_USER_NAME,
            TEST_USER_GROUPS,
            TEST_USER_DOMAIN_US,
            eula_signed=True,
        )
    )

    @task
    def login(self):
        with self.client.request(
            "GET",
            f"{TEST_USER_DOMAIN}/login",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive",
                "Host": "cloudumidev.com:3000",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            },
            catch_response=True,
        ) as resp:
            assert resp.status_code == 200

    @task
    def user_profile_auth(self):
        with self.rest(
            "GET",
            f"{TEST_USER_DOMAIN}/api/v2/user_profile",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Cookie": f"noq_auth={self.token}",
                "Host": "cloudumidev.com:3000",
                "Referer": f"{TEST_USER_DOMAIN}/login",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sec-ch-ua": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            },
        ) as resp:
            assert resp.status_code == 200


if __name__ == "__main__":
    run_single_user(LoadTest)
