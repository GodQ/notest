from __future__ import absolute_import
import sys
import string

"""
Parsing utilities, pulled out so they can be used in multiple modules
"""


def encode_unicode_bytes(my_string):
    """ Shim function, converts Unicode to UTF-8 encoded bytes regardless of the source format
        Intended for python 3 compatibility mode, and b/c PyCurl only takes raw bytes
    """
    if not isinstance(my_string, str):
        my_string = repr(my_string)

    if isinstance(my_string, str):
        return my_string.encode('utf-8')
    elif isinstance(my_string, bytes):
        return my_string


# TODO create a full class that extends string.Template
def safe_substitute_unicode_template(templated_string, variable_map):
    """ Perform string.Template safe_substitute on unicode input with unicode variable values by using escapes
        Catch: cannot accept unicode variable names, just values
        Returns a Unicode type output, if you want UTF-8 bytes, do encode_unicode_bytes on it
    """
    return string.Template(templated_string).safe_substitute(variable_map)


def safe_to_json(in_obj):
    """ Safely get dict from object if present for json dumping """
    if isinstance(in_obj, bytearray):
        return str(in_obj)
    if hasattr(in_obj, '__dict__'):
        return in_obj.__dict__
    try:
        return str(in_obj)
    except:
        return repr(in_obj)


def flatten_dictionaries(input):
    """ Flatten a list of dictionaries into a single dictionary, to allow flexible YAML use
      Dictionary comprehensions can do this, but would like to allow for pre-Python 2.7 use
      If input isn't a list, just return it.... """
    output = dict()
    if isinstance(input, list):
        for map in input:
            output.update(map)
    else:  # Not a list of dictionaries
        output = input
    return output


def lowercase_keys(input_dict):
    """ Take input and if a dictionary, return version with keys all lowercase and cast to str """
    if not isinstance(input_dict, dict):
        return input_dict
    safe = dict()
    for key, value in input_dict.items():
        safe[str(key).lower()] = value
    return safe


def safe_to_bool(input):
    """ Safely convert user input to a boolean, throwing exception if not boolean or boolean-appropriate string
      For flexibility, we allow case insensitive string matching to false/true values
      If it's not a boolean or string that matches 'false' or 'true' when ignoring case, throws an exception """
    if isinstance(input, bool):
        return input
    elif isinstance(input, str) and input.lower() == 'false':
        return False
    elif isinstance(input, str) and input.lower() == 'true':
        return True
    else:
        raise TypeError(
            'Input Object is not a boolean or string form of boolean!')
