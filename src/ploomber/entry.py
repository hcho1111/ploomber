"""
Warning: this code is highly experimental
"""

# TODO: print enviornment content on help and maybe on any other command
# it is useful for debugging purposes
# TODO: this should also work if the function is not decorated with @with_env

import sys
import importlib
import argparse
import inspect

from numpydoc.docscrape import NumpyDocString

# TODO: move this here
from ploomber.env.EnvDict import flatten_dict


# TODO: what to do if numpydoc is not installed? required it? fail silently?
# output  a warning?
def parse_doc(doc):
    """
    Convert numpydoc docstring to a list of dictionaries
    """
    if doc is None:
        return {'params': {}, 'summary': None}

    doc = NumpyDocString(doc)
    parameters = {p.name: {'desc': ' '.join(p.desc), 'type': p.type}
                  for p in doc['Parameters']}
    summary = doc['Summary']
    return {'params': parameters, 'summary': summary}


def _parse_module(s):
    parts = s.split('.')

    if len(parts) < 2:
        raise ImportError('Invalid module name, must be a dot separated '
                          'string, with at least '
                          '[module_name].[function_name]')

    return '.'.join(parts[:-1]), parts[-1]


def main():
    parser = argparse.ArgumentParser()

    n_pos = len([arg for arg in sys.argv if not arg.startswith('-')])

    parser.add_argument('entry_point', help='Entry point (DAG)')

    if n_pos < 2:
        args = parser.parse_args()
    else:
        parser.add_argument('action', help='Action to execute')

        mod, name = _parse_module(sys.argv[1])

        try:
            module = importlib.import_module(mod)
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError('Could not import module "{}", '
                                      'make sure it is available in the '
                                      'current python environment'.
                                      format(mod))

        try:
            entry = getattr(module, name)
        except AttributeError as e:
            raise AttributeError('Could not get attribute "{}" from module '
                                 '"{}", make sure such function exists'
                                 .format(mod, name)) from e

        flat_env_dict = flatten_dict(entry._env_dict)

        doc = parse_doc(entry.__doc__)

        def get_desc(arg):
            arg_data = doc['params'].get(arg)
            return None if arg_data is None else arg_data['desc']

        sig = inspect.signature(entry)

        defaults = {k: v.default for k, v in sig.parameters.items()
                    if v.default != inspect._empty}
        required = [k for k, v in sig.parameters.items()
                    if v.default == inspect._empty]

        for arg, default in defaults.items():
            parser.add_argument('--'+arg,
                                help=get_desc(arg))

        required.remove('env')

        for arg in required:
            parser.add_argument(arg, help=get_desc(arg))

        for arg, val in flat_env_dict.items():
            parser.add_argument('--'+arg, help='Default: {}'.format(val))

        args = parser.parse_args()

        kwargs = {key: getattr(args, key) for key in required}

        print(getattr(entry(**kwargs), args.action)())


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error:', e)
        sys.exit(1)
