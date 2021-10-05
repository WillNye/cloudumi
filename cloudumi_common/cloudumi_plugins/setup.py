"""
cloudumi_plugins
==============

ConsoleMe SaaS plugins for ConsoleMe

"""
import distutils.cmd
import distutils.log
import os
from shutil import rmtree

from setuptools import find_packages, setup


class CleanAllCommand(distutils.cmd.Command):
    """Docstring for public class."""

    description = "remove extra build files"
    user_options = []
    dirname = os.path.dirname(os.path.realpath(__file__))

    def initialize_options(self):
        """Docstring for public method."""
        pass

    def finalize_options(self):
        """Docstring for public method."""
        pass

    def run(self):
        """Docstring for public method."""
        targets = [
            ".cache",
            ".coverage.py27",
            ".coverage.py36",
            ".tox",
            "coverage-html.py27",
            "coverage-html.py36",
            "consoleme.egg-info",
            "consoleme/__pycache__",
            "test/__pycache__",
        ]
        for t in targets:
            path = os.path.join(self.dirname, t)
            if os.path.isfile(path):
                self.announce(
                    "removing file: {}".format(path), level=distutils.log.INFO
                )
                os.remove(path)
            elif os.path.isdir(path):
                self.announce(
                    "removing directory: {}".format(path), level=distutils.log.INFO
                )
                rmtree(path)


install_requires = []

setup(
    name="cloudumi_plugins",
    version="0.1",
    author="Curtis Castrapel",
    author_email="ccastrapel@netflix.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    setup_requires=["setupmeta"],
    python_requires=">=3.8",
    entry_points={
        "cloudumi.plugins": [
            # Change the name of the entry point for your plugin here, and in your configuration
            "cmsaas_config = cloudumi_plugins.plugins.config.config:Config",
            "cmsaas_auth = cloudumi_plugins.plugins.auth.auth:Auth",
            "cmsaas_aws = cloudumi_plugins.plugins.aws.aws:Aws",
            "cmsaas_celery_tasks = cloudumi_plugins.plugins.celery_tasks.celery_tasks:internal_schedule",
            "cmsaas_celery_tasks_functions = cloudumi_plugins.plugins.celery_tasks.celery_tasks:CeleryTasks",
            "cmsaas_metrics = cloudumi_plugins.plugins.metrics.metrics:Metric",
            "cmsaas_policies = cloudumi_plugins.plugins.policies.policies:Policies",
            "cmsaas_group_mapping = cloudumi_plugins.plugins.group_mapping.group_mapping:GroupMapping",
            "cmsaas_internal_routes = cloudumi_plugins.plugins.internal_routes.internal_routes:InternalRoutes",
        ]
    },
    cmdclass={"cleanall": CleanAllCommand},
)
