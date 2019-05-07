from pyresttest.common_test import CommonTest
OPERATIONS = dict()


def register_operations(typename, parse_function):
    """ Register a new tool for use in testing
        typename is the new tool type name (must not already exist)
        parse_function will run the tool
    """
    if not isinstance(typename, str):
        raise TypeError(
            'Generator type name {0} is invalid, must be a string'.format(typename))
    if typename in OPERATIONS:
        raise ValueError(
            'Generator type named {0} already exists'.format(typename))
    OPERATIONS[typename] = parse_function


def get_operation_function(typename):
    return OPERATIONS.get(typename.lower())


# Demo operation
def demo_operation(config, context=None):
    pass


class Operation(CommonTest):
    test_type = "operation"
    config = None
    group = "operation"
