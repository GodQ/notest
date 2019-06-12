

TEST_RUNNERS = dict()


def register_test_runner(name, parse_function):
    ''' Registers a test runner for use by this library
        Name is the string name for test runner

        Parse function does parse(config_node) and returns a test runner object
        test runner functions have signature:
            run_test(context=None)
    '''

    name = name.lower()
    if name in TEST_RUNNERS:
        raise Exception("Test Runner exists with this name: {0}".format(name))

    TEST_RUNNERS[name] = parse_function


def get_test_runner_parser(name):
    name = name.lower()
    if name not in TEST_RUNNERS:
        raise Exception("Test Runner {} does not exist".format(name))
    return TEST_RUNNERS[name]


from notest.http_test_runner.http_test import HttpTest
register_test_runner("http_test", HttpTest.parse_from_dict)
