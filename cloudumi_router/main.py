# Receives requests into CloudUmi
# Determines host
# Authenticates client according to host settings
# Sends async request to other container
# TODO: Dev mode only:
import ptvsd
ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)


import uvicorn
import httpx
from fastapi import FastAPI, Response, Request

app = FastAPI()

path_mapping = {
    "healthcheck": "http://cloudumi_healthcheck:8090/healthcheck"
}

frontend = "http://cloudumi_frontend/"


@app.get("/{path:path}")
async def wildcard_get(path: str, request: Request, response: Response):
    print(path)
    reverse_proxy_route = path_mapping.get(path)
    if not reverse_proxy_route:
        # return frontend
        reverse_proxy_route = frontend
    async with httpx.AsyncClient() as client:
        # TODO: Data and headers and query string
        proxy = await client.get(reverse_proxy_route)
    response.body = proxy.content
    response.status_code = proxy.status_code
    return response


@app.post("/{path:path}")
async def wildcard_post(path: str, request: Request, response: Response):
    print(path)
    path_map = path_mapping[path]
    async with httpx.AsyncClient() as client:
        # TODO: Data and headers and querystring
        proxy = await client.post(path_map)
    response.body = proxy.content
    response.status_code = proxy.status_code
    return response


@app.put("/{path:path}")
async def wildcard_put(path: str, request: Request, response: Response):
    print(path)
    path_map = path_mapping[path]
    async with httpx.AsyncClient() as client:
        # TODO: Data and headers and querystring
        proxy = await client.put(path_map)
    response.body = proxy.content
    response.status_code = proxy.status_code
    return response
#
# @app.get("/healthcheck")
# async def healthcheck_get(response: Response):
#     async with httpx.AsyncClient() as client:
#         proxy = await client.get(f"http://cloudumi_healthcheck:8090/healthcheck")
#     response.body = proxy.content
#     response.status_code = proxy.status_code
#     return response
#
#
# @app.get("/auth")
# async def auth_get(response: Response):
#     async with httpx.AsyncClient() as client:
#         proxy = await client.get(f"http://cloudumi_healthcheck:8081/auth")
#     response.body = proxy.content
#     response.status_code = proxy.status_code
#     return response
#
# @app.post("/auth")
# async def auth_post(response: Response):
#     async with httpx.AsyncClient() as client:
#         proxy = await client.get(f"http://cloudumi_healthcheck:8081/auth")
#     response.body = proxy.content
#     response.status_code = proxy.status_code
#     return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)