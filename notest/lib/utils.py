
import string
import yaml
import json


def templated_string(src, context=None):
    if not context:
        return src
    if not isinstance(context, dict):
        context = context.get_values()
    src = string.Template(src).safe_substitute(context)
    return src


def templated_var(data, context=None):
    if not context:
        return data
    if isinstance(data, str) and data.find("$") > -1:
        res = templated_string(data, context)
        return res
    elif isinstance(data, dict) and len(data) == 1 and "template" in data:
        src = data["template"]
        res = templated_string(src, context)
        return res
    else:
        return data


def read_file(path):
    """ Read an input into a file, doing necessary conversions around relative path handling """
    with open(path, "r") as f:
        string = f.read()
        f.close()
    return string


def read_test_file(path):
    """ Read test file at 'path' in yaml/yml or json"""
    content = read_file(path)
    try:
        teststruct = yaml.safe_load(content)
    except:
        teststruct = json.loads(content)
    return teststruct