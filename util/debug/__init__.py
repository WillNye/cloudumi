import os
import ptvsd

# To debug over network, set corresponding env var to 0.0.0.0
DEBUG_HOST = os.getenv('DEBUG_HOST', 'localhost')

# Set the debug port to attach to
DEBUG_PORT = os.getenv('DEBUG_PORT', 9092)

# Set this to true in the environment if debugging is desired
DEBUG_ENABLED = os.getenv('DEBUG', False)

if DEBUG_ENABLED:
    ptvsd.enable_attach(address=('localhost', DEBUG_PORT), redirect_output=True)
    print("Debugger listening on port 9092. Waiting for debugger to attach...")
    ptvsd.wait_for_attach()