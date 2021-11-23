import pip
from pip._internal.network.session import PipSession
from pip._internal.req import parse_requirements
from setuptools import setup

requirements = parse_requirements("requirements.txt", session=PipSession())
test_requirements = parse_requirements("requirements-test.txt", session=PipSession())

if tuple(map(int, pip.__version__.split("."))) >= (20, 1):
    reqs = [str(ir.requirement) for ir in requirements]
else:
    reqs = [str(ir.req) for ir in requirements]

setup(
    name="cloudumi_config",
    versioning="distance",
    setup_requires="setupmeta",
    install_requires=reqs,
)
