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
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
    }

    token = asyncio.run(
        generate_jwt_token(
            TEST_USER_NAME,
            TEST_USER_GROUPS,
            TEST_USER_DOMAIN_US,
            eula_signed=True,
            tenant_active=True,
        )
    )

    @task
    def user_profile_auth(self):
        resp = self.client.request(
            "GET",
            "/api/v2/user_profile",
            headers={
                "Host": TEST_USER_DOMAIN,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Cookie": f"noq_auth={self.token}",
                "Referer": f"{TEST_USER_DOMAIN}/login",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sec-ch-ua": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "X-Forwarded-Host": TEST_USER_DOMAIN,
                "X-Forwarded-For": "127.0.0.1",
            },
        )

        if resp.status_code != 200:
            print(TEST_USER_DOMAIN)
            print(self.host)
            print(resp.text)
            print(f"Error response: {resp.status_code}")

    @task
    def auth_endpoint_without_auth(self):
        # This will return a non 200 since it doesn't contain an auth cookie
        with self.client.request(
            "GET",
            "/api/v1/auth",
            headers={
                "Host": TEST_USER_DOMAIN,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": f"{TEST_USER_DOMAIN}/login",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sec-ch-ua": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "X-Forwarded-Host": TEST_USER_DOMAIN,
                "X-Forwarded-For": "127.0.0.1",
            },
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.success()

    @task
    def healthcheck_vanilla_tornado_handler(self):
        # This should be the fastest endpoint, because it
        # uses the native tornado.web.RequestHandler
        resp = self.client.request(
            "GET",
            "/healthcheck_vanilla",
            headers={
                "Host": TEST_USER_DOMAIN,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": f"{TEST_USER_DOMAIN}/login",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sec-ch-ua": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "X-Forwarded-Host": TEST_USER_DOMAIN,
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        if resp.status_code != 200:
            print(TEST_USER_DOMAIN)
            print(self.host)
            print(resp.text)
            print(f"Error response: {resp.status_code}")

    @task
    def healthcheck(self):
        resp = self.client.request(
            "GET",
            "/healthcheck",
            headers={
                "Host": TEST_USER_DOMAIN,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": f"{TEST_USER_DOMAIN}/login",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sec-ch-ua": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "X-Forwarded-Host": TEST_USER_DOMAIN,
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        if resp.status_code != 200:
            print(TEST_USER_DOMAIN)
            print(self.host)
            print(resp.text)
            print(f"Error response: {resp.status_code}")


if __name__ == "__main__":
    run_single_user(LoadTest)
