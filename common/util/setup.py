import os
from shutil import rmtree

import distutils.cmd
import distutils.log
import pip
from setuptools import find_packages, setup

if tuple(map(int, pip.__version__.split("."))) >= (19, 3, 0):
    from pip._internal.network.session import PipSession
    from pip._internal.req import parse_requirements
elif tuple(map(int, pip.__version__.split("."))) >= (10, 0, 0):
    from pip._internal.download import PipSession
    from pip._internal.req import parse_requirements
else:
    from pip.download import PipSession
    from pip.req import parse_requirements


class CleanAllCommand(distutils.cmd.Command):
    """Docstring for public class."""

    description = "remove extra build files"
    user_options = []
    dirname = os.path.dirname(os.path.realpath(__file__))

    def initialize_options(self):
        """Docstring for public method."""

    def finalize_options(self):
        """Docstring for public method."""

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
                self.announce(f"removing file: {path}", level=distutils.log.INFO)
                os.remove(path)
            elif os.path.isdir(path):
                self.announce(f"removing directory: {path}", level=distutils.log.INFO)
                rmtree(path)


requirements = parse_requirements("requirements.txt", session=PipSession())
test_requirements = parse_requirements("requirements-test.txt", session=PipSession())

if tuple(map(int, pip.__version__.split("."))) >= (20, 1):
    reqs = [str(ir.requirement) for ir in requirements]
    test_reqs = [str(ir.requirement) for ir in test_requirements]
else:
    reqs = [str(ir.req) for ir in requirements]
    test_reqs = [str(ir.req) for ir in test_requirements]

setup(
    name="common",
    author="Curtis Castrapel",
    author_email="ccastrapel@gmail.com",
    python_requires=">=3.8",
    install_requires=reqs,
    tests_require=test_reqs,
    setup_requires=["setupmeta"],
    extras_require={"test": ["tox"]},
    packages=find_packages(exclude=("tests",)),
    entry_points={},
    cmdclass={"cleanall": CleanAllCommand},
    include_package_data=True,
    versioning="devcommit",
    zip_safe=False,
)


setup(name="common", versioning="distance", setup_requires="setupmeta")
