from io import StringIO

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
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.representer.ignore_aliases = lambda *data: True
yaml.width = 4096
