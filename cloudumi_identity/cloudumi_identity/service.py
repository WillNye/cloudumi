import asyncio
import os
from concurrent import futures
from signal import SIGTERM, signal

import grpc

from cloudumi_common.config import config
from cloudumi_protobufs import identity_service_pb2_grpc


class GroupManagementService(identity_service_pb2_grpc.GroupManagementServiceServicer):
    # TODO: Authorization check?
    async def GroupManagement(self, request, context):
        print(request)


async def serve():
    # interceptors = [ErrorLogger()]
    server = grpc.aio.server()
    identity_service_pb2_grpc.add_GroupManagementServiceServicer_to_server(
        GroupManagementService(), server
    )
    server.add_insecure_port("[::]:50051")
    await server.start()

    def handle_sigterm(*_):
        print("Received shutdown signal")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        print("Shut down gracefully")

    signal(SIGTERM, handle_sigterm)
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
