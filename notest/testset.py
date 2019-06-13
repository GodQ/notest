import json

from notest.common_test import CommonTest
from notest.lib.parsing import safe_to_json

DEFAULT_TIMEOUT = 30


class TestSetConfig:
    """ Configuration for a test run """
    testset_name = None
    timeout = DEFAULT_TIMEOUT  # timeout of tests, in seconds
    request_client = None  # requests or pycurl
    retries = 0  # Retries on failures
    interactive = False
    verbose = False
    ssl_insecure = True

    # Binding and creation of generators
    collect_import_result = False
    variable_binds = None
    generators = None  # Map of generator name to generator function
    extract = None  # extract several variable in context after this test set run
    data_driven_generator = None
    data_driven_generator_name = None
    working_directory = None

    def set_default_base_url(self, url):
        self.variable_binds['default_base_url'] = url

    def set_variable_binds(self, k, v):
        self.variable_binds[k] = v

    def __str__(self):
        return json.dumps(self, default=safe_to_json)


class TestSet(CommonTest):
    test_type = "testset"
    name = None
    group = "testset"
    input = None
    extract = None
    file_path = None

    """ Encapsulates a set of tests and test configuration for them """
    tests = list()
    config = TestSetConfig()
    subtestsets = dict()

    def __init__(self):
        self.config = TestSetConfig()
        self.tests = list()
        self.subtestsets = dict()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)