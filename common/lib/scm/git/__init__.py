import os
import shutil
import tempfile
from typing import Optional

import git

from common.lib.asyncio import aio_wrapper


class Repository:
    def __init__(self, repo_url, repo_name, git_email):
        self.tempdir = tempfile.mkdtemp()
        self.repo_url = repo_url
        self.git_email = git_email
        self.repo = None
        self.repo_name = repo_name
        self.git = None

    async def clone(self, no_checkout=True, depth: Optional[int] = None):
        args = []
        kwargs = {}
        if no_checkout:
            args.append("-n")
        args.append(self.repo_url)
        if depth:
            kwargs["depth"] = depth
        await aio_wrapper(git.Git(self.tempdir).clone, *args, **kwargs)
        self.repo = git.Repo(os.path.join(self.tempdir, self.repo_name))
        self.repo.config_writer().set_value("user", "name", "Noq").release()
        if self.git_email:
            self.repo.config_writer().set_value(
                "user", "email", self.git_email
            ).release()
        self.git = self.repo.git
        return self.repo

    async def cleanup(self):
        await aio_wrapper(shutil.rmtree, self.tempdir)
