from setuptools import setup

setup(
    name="cloudumi",
    versioning="distance",  # Optional, would activate tag-based versioning
    setup_requires="setupmeta",  # This is where setupmeta comes in
    packages=["api", "common", "identity", "plugins"],
)
