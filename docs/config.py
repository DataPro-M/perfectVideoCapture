"""Config Parser."""

import configparser
from typing import Dict, Tuple


def read_ini(file_path: str) -> Tuple[Dict, Dict]:
    """Read the config file."""
    config = configparser.ConfigParser()
    config.read(file_path)
    # ConfigParsers sets keys which have no value
    # (like `--force` above) to `None`. Thus we
    # need to substitute all `None` with `True`.
    default_arguments = {
        key: (True if value is None else value)
        for key, value in config.items("defaultArgs")
    }

    # convert config to dict
    config_dict = {s: dict(config.items(s)) for s in config.sections()}
    return config_dict, default_arguments


def merge(dict_1: Dict, dict_2: Dict) -> Dict:
    """Merge two dictionaries.

    Values that evaluate to true take priority over falsy values.
    `dict_1` takes priority over `dict_2`.
    """
    dict_data = {
        str(key): (dict_1.get(key) or dict_2.get(key))
        for key in set(dict_2) | set(dict_1)
    }
    return dict_data
