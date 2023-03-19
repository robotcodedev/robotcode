import sys

from robotcode.core.dataclasses import from_dict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .model import Configuration


def create_from_toml(__s: str) -> Configuration:
    dict_data = tomllib.loads(__s)
    return from_dict(dict_data, Configuration)
