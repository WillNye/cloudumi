# TODO: Figure out how to get debugpy to work with Bazel symlinks
# import debugpy
# debugpy.listen(("localhost", 9092))
# print("Debugger listening on port 9092. Waiting for debugger to attach...")
# debugpy.wait_for_client()  # blocks execution until client is attached

import ptvsd

ptvsd.enable_attach(address=("localhost", 9092), redirect_output=True)
print("Debugger listening on port 9092. Waiting for debugger to attach...")
ptvsd.wait_for_attach()

import api.__main__  # noqa: E402
