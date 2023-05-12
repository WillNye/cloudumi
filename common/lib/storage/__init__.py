import os
from pathlib import Path
from typing import Any, Union

import aiofiles
import aiofiles.os
from aiopath import AsyncPath

from common.config.tenant_config import TenantConfig


class TenantFileStorageHandler:
    def __init__(self, tenant: str):
        self.tenant: str = tenant
        self.tenant_config = TenantConfig(tenant)

    async def get_tenant_file_path(self, file_path: Union[str, Path]) -> str:
        file_path = str(file_path)
        tenant_storage_base_path = self.tenant_config.tenant_storage_base_path
        if not tenant_storage_base_path.startswith("/"):
            raise Exception("Tenant storage base path must start with /")

        if file_path.startswith(tenant_storage_base_path):
            full_file_path = file_path
        else:
            if not isinstance(file_path, str) and not isinstance(file_path, Path):
                raise Exception("File_path must be a string or a Path")
            elif file_path.replace(tenant_storage_base_path, "").startswith("/"):
                raise Exception("File_path must not start with /")
            elif not self.tenant_config.tenant_storage_base_path.startswith("/"):
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

    async def write_file(self, file_path: str, level: str, data: Any):
        full_file_path = Path(await self.get_tenant_file_path(file_path))
        if level in {"w", "wb"}:
            await aiofiles.os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
        with open(full_file_path, level) as f:
            f.write(data)
        # TODO: aiofiles for some reason sometimes appends extra characters at the end of the file
        # async with aiofiles.open(full_file_path, level) as f:
        #     await f.write(data)

    async def read_file(self, file_path: str, level: str):
        full_file_path = await self.get_tenant_file_path(file_path)
        async with aiofiles.open(full_file_path, level) as f:
            return await f.read()
