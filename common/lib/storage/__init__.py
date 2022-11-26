import os
from typing import Any

import aiofiles
import aiofiles.os
from aiopath import AsyncPath

from common.config.tenant_config import TenantConfig


class TenantFileStorageHandler:
    def __init__(self, tenant):
        self.tenant = tenant
        self.tenant_config = TenantConfig(tenant)

    async def get_tenant_file_path(self, file_path: str):
        if not isinstance(file_path, str):
            raise Exception("File_path must be a string")
        if file_path.startswith("/"):
            raise Exception("File_path must not start with /")
        if not self.tenant_config.tenant_storage_base_path.startswith("/"):
            raise Exception("Tenant storage base path must start with /")
        full_file_path = os.path.join(
            self.tenant_config.tenant_storage_base_path, file_path
        )
        if ".." in full_file_path:
            raise Exception("Invalid file path. `..` is not allowed in path")
        return full_file_path

    async def tenant_file_exists(self, file_path: str):
        full_path_str = await self.get_tenant_file_path(file_path)
        full_path = AsyncPath(full_path_str)
        return await full_path.exists()

    # async def open_file(self, file_path: str, *args, **kwargs):
    #     full_file_path = await self.get_tenant_file_path(file_path)

    #     if args[0] in ["w", "wb"]:
    #         await aiofiles.os.makedirs(
    #             os.path.dirname(full_file_path),
    #             exist_ok=True
    #         )
    #     return aiofiles.open(full_file_path, *args, **kwargs)

    async def write_file(self, file_path: str, level: str, data: Any):
        full_file_path = await self.get_tenant_file_path(file_path)
        if level in {"w", "wb"}:
            await aiofiles.os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
        async with aiofiles.open(full_file_path, level) as f:
            await f.write(data)
