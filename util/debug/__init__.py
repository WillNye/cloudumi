import os
import sys

# Set this to true in the environment if debugging is desired
DEBUG_ENABLED = os.getenv("DEBUG", False)
if DEBUG_ENABLED:
    import ptvsd

    # To debug over network, set corresponding env var to 0.0.0.0
    DEBUG_HOST = os.getenv("DEBUG_HOST", "localhost")

    # Set the debug port to attach to
    DEBUG_PORT = os.getenv("DEBUG_PORT", 9092)

    print(" ===> DEBUG ENABLED THERE GOOD BUDDYS <=== ")
    ptvsd.enable_attach(address=(DEBUG_HOST, DEBUG_PORT), redirect_output=True)
    print(f"Debugger listening on port {DEBUG_PORT}. Waiting for debugger to attach...")
    ptvsd.wait_for_attach()

FAULTHANDLER_ENABLED = os.getenv("FAULTHANDLER_ENABLED", False)
if FAULTHANDLER_ENABLED:
    import faulthandler

    faulthandler.enable(file=sys.stderr, all_threads=True)
    faulthandler.dump_traceback_later(10, repeat=True, file=sys.stderr, exit=False)
