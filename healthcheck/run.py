import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "healthcheck.main:app",
        host="0.0.0.0",
        port=8090,
        reload=True,
        debug=True,
        workers=3,
    )
