"""
Usage:
  config.py [--file=<file_path-path>] [--width=<pixel>] 
            [--height=<pixel>] [--fps=<int-fps>]
            [--stream_name=<stream-name>] [--service_name=<service-name>] 
  config.py -h | --help | --version

"""
import configparser
from docopt import docopt
from pprint import pprint


def read_ini(file_path):    

    config = configparser.ConfigParser()
    config.read(file_path)
    # ConfigParsers sets keys which have no value
    # (like `--force` above) to `None`. Thus we
    # need to substitute all `None` with `True`.
    default_arguments = dict((key, True if value is None else value)
                            for key, value in config.items('defaultArgs'))

    # convert config to dict
    config_dict = {s: dict(config.items(s)) for s in config.sections()}
    return config_dict, default_arguments
 
def merge(dict_1, dict_2):
    """Merge two dictionaries.
    Values that evaluate to true take priority over falsy values.
    `dict_1` takes priority over `dict_2`.
    """
    dict_data =  dict((str(key), dict_1.get(key) or dict_2.get(key))
                    for key in set(dict_2) | set(dict_1))
    return proper_convert_dataset(dict_data)

# easy add property to a python class dynamically
class C(object):
    # zip keys and values
    def __init__(self, ks, vs):
        self.__dict__ = dict(zip(ks, vs))

def proper_convert_dataset(dict_data):
    dict_data = {k.replace(u'--', '') : v for k, v in dict_data.items()}
    return C( [*dict_data], [*dict_data.values()])

if __name__ == '__main__':
    import os
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    initfile = os.path.join(thisfolder, 'config.ini')
    
    config, ini_config = read_ini(initfile)
    arguments = docopt(__doc__, version='0.1.1rc')
    
    print('\nINI config:')
    pprint(ini_config)
    print(f"The default fps: {ini_config['--fps']}")

    # Arguments take priority over INI, INI takes priority over JSON:
    result = merge(arguments, ini_config)
    print('\nUser config:')
    pprint(vars(result))
    
    print(f'The fps arg is: {result.fps}') # instead of result['--fps']   
