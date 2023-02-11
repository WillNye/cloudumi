import pytest


@pytest.mark.asyncio
async def test_retrieve_items(app_listening_on_port, authenticated_client_session):
    port = app_listening_on_port
    async for session in authenticated_client_session:
        async with session.post(
            f"http://localhost:{port}/api/v4/roles/access", json={}
        ) as resp:
            assert resp.status == 200
            res_j = await resp.json()
            assert "data" in res_j.keys()
            data = res_j.get("data")
            assert "access_roles" in data
            access_roles = data.get("access_roles")
            assert len(access_roles) > 0


@pytest.mark.asyncio
async def test_filter_retrieve_items(
    app_listening_on_port, authenticated_client_session
):
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
                        "value": "admin_user@noq.dev",
                    }
                ],
                "operation": "and",
            },
        }
    }
    port = app_listening_on_port
    async for session in authenticated_client_session:
        async with session.post(
            f"http://localhost:{port}/api/v4/roles/access", json=body
        ) as resp:
            assert resp.status == 200
            res_j = await resp.json()
            assert "data" in res_j.keys()
            data = res_j.get("data")
            assert "access_roles" in data
            access_roles = data.get("access_roles")
            assert len(access_roles) > 0


@pytest.mark.asyncio
async def test_filter_not_found_returns_500(
    app_listening_on_port, authenticated_client_session
):
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
    port = app_listening_on_port
    async for session in authenticated_client_session:
        async with session.post(
            f"http://localhost:{port}/api/v4/roles/access", json=body
        ) as resp:
            assert resp.status == 500
