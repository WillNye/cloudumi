from io import StringIO
from multiprocessing import Pool
from uuid import UUID

from ruamel.yaml import YAML


class CloudUmiYaml(YAML):
    def dump(self, data, stream=None, **kw):
        inefficient = False
        if stream is None:
            inefficient = True
            stream = StringIO()
        YAML.dump(self, data, stream, **kw)
        if inefficient:
            return stream.getvalue()


typ = "rt"
yaml = CloudUmiYaml(typ=typ)
yaml_safe = CloudUmiYaml(typ="safe")
yaml_safe.register_class(UUID)
yaml_pure = CloudUmiYaml(typ="safe", pure=True)
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.representer.ignore_aliases = lambda *data: True

# Ability to serialize UUID objects
yaml.register_class(UUID)

yaml.width = 4096


def safe_yaml_load(file_path) -> dict:
    # It isn't pretty to look at but works around the memory leak in ruamel.yaml
    with Pool(1) as p:
        return p.map(yaml_safe.load, [open(file_path)])[0]
