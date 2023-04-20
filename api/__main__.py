"""Entrypoint. To run service, set CONFIG_LOCATION environmental variable and run
python -m api.__main__"""

# uvloop and xmlsec Hack
# Essentially we are installing these depedendencies into the build environment using the //docker BUILD file (reference:
# docker/base/BUILD)
# Tech Debt ticket: SAAS-95, SAAS-94
import os
import signal

if os.getenv("DEBUG"):
    os.system("systemctl start ssh")
#############

import asyncio
import logging

import tornado.autoreload
import tornado.httpserver
import tornado.ioloop
import uvloop
from tornado.platform.asyncio import AsyncIOMainLoop

from api.routes import make_app
from common.config import config
from common.lib.plugins import fluent_bit, get_plugin_by_name
from common.scripts.initialize_postgres import run_alembic_migrations
from functional_tests import run_tests as functional_tests

log = config.get_logger()

configured_profiler = config.get("_global_.profiler")
if configured_profiler:
    if configured_profiler == "memray":
        from memray import Tracker

        profiler = Tracker("/tmp/memray.bin")
        profiler.__enter__()
    elif configured_profiler == "pprofile":
        import pprofile

        profiler = pprofile.Profile()
        profiler.enable()
    elif configured_profiler == "yappi":
        import yappi

        yappi.start()
    else:
        raise ValueError(f"Profiler {configured_profiler} not supported")

# Run functional tests
functional_tests.run()


def main():
    if config.get("_global_.sso.create_mock_jwk"):
        app = make_app(jwt_validator=lambda x: {})
    else:
        app = make_app()
    return app


if config.get("_global_.tornado.uvloop", True):
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
AsyncIOMainLoop().install()
app = main()
if config.get("_global_.elastic_apn.enabled"):
    from elasticapm.contrib.tornado import ElasticAPM

    app.settings["ELASTIC_APM"] = {
        "SERVICE_NAME": config.get("_global_.elastic_apn.service_name", "cloudumi"),
        "SECRET_TOKEN": config.get("_global_.elastic_apn.secret_token"),
        "SERVER_URL": config.get("_global_.elastic_apn.server_url"),
    }
    apm = ElasticAPM(app)


async def shutdown(signal, loop):
    """Cleanup tasks tied to the service's shutdown."""
    logging.info(f"Received exit signal {signal.name}...")
    logging.info("Closing database connections")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    [task.cancel() for task in tasks]

    logging.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks)
    logging.info("Flushing metrics")
    loop.stop()


def init():
    stats = get_plugin_by_name(
        config.get("_global_.plugins.metrics", "cmsaas_metrics")
    )()
    if __name__ in ["__main__", "api.__main__"]:
        port = config.get("_global_.tornado.port", 8092)
        stats.count("tornado.start")

        server = tornado.httpserver.HTTPServer(app)

        if port:
            server.bind(port, address=config.get("_global_.tornado.address"))

        server.start()  # forks one process per cpu

        run_alembic_migrations()

        log.debug({"message": "Server started", "port": port})
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        fluent_bit.add_fluent_bit_service()
        loop = asyncio.get_event_loop()
        for s in signals:
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(shutdown(s, loop))
            )
        try:
            loop.run_forever()
        finally:
            loop.close()
            fluent_bit.remove_fluent_bit_service()
            if configured_profiler:
                if configured_profiler == "pprofile":
                    profiler.disable()
                    with open("/tmp/noq_profile.pprof", "w") as f:
                        profiler.callgrind(f)
                if configured_profiler == "memray":
                    profiler.__exit__(None, None, None)
                if configured_profiler == "yappi":
                    yappi.stop()
                    yappi.get_func_stats().print_all()
                    yappi.get_thread_stats().print_all()
                    stats = yappi.get_func_stats()
                    stats.save("/tmp/yappi.callgrind", type="callgrind")
            logging.info("Successfully shutdown the service.")


if os.getenv("RUNTIME_PROFILE", "API") == "API":
    init()
