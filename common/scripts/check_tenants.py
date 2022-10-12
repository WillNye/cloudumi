import json
import sys
import urllib.request
from typing import List


def check_tenants(tenant_urls: List[str]):
    tenant_urls = json.loads("".join(lines))
    for tenant_url in tenant_urls:
        print(f"Testing {tenant_url}")
        res = urllib.request.urlopen(tenant_url)
        finalurl = res.geturl()
        print(finalurl)
        assert res.code == 200


if __name__ == "__main__":
    lines = []
    for line in sys.stdin:
        lines.append(line)

    tenant_urls = json.loads("".join(lines))
    check_tenants(tenant_urls)
