"""Config Parser."""

import configparser


def read_ini(file_path):
    """Read the config file."""
    config = configparser.ConfigParser()
    config.read(file_path)
    # ConfigParsers sets keys which have no value
    # (like `--force` above) to `None`. Thus we
    # need to substitute all `None` with `True`.
    default_arguments = {
        (key, True if value is None else value)
        for key, value in config.items("defaultArgs")
    }
    default_arguments = {x: y for x, y in default_arguments}

    # convert config to dict
    config_dict = {s: dict(config.items(s)) for s in config.sections()}
    return config_dict, default_arguments


def merge(dict_1, dict_2):
    """Merge two dictionaries.

    Values that evaluate to true take priority over falsy values.
    `dict_1` takes priority over `dict_2`.
    """
    dict_data = {
        (str(key), dict_1.get(key) or dict_2.get(key))
        for key in set(dict_2) | set(dict_1)
    }
    return proper_convert_dataset(dict_data)


# easy add property to a python class dynamically
class C(object):
    """Convert the dataset to proper format."""

    # zip keys and values
    def __init__(self, ks, vs):
        """Initialize the class."""
        self.__dict__ = dict(zip(ks, vs))


def proper_convert_dataset(dict_data):
    """Convert the dataset to a proper format."""
    dict_data = {k.replace("--", ""): v for k, v in dict_data}
    return C([*dict_data], [*dict_data.values()])
