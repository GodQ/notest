from .import_base import *
import json
import logging

logger = logging.getLogger('pyresttest.http_test')

from pyresttest.clients.http_client import HttpClient
from pyresttest.clients.http_auth_type import HttpAuthType
from pyresttest.lib.utils import templated_var
from pyresttest.test_result import TestResult

"""
Pull out the Test objects and logic associated with them
This module implements the internal responsibilities of a test object:
- Test parameter/configuration storage
- Templating for tests
- Parsing of test configuration from results of YAML read
"""

DEFAULT_TIMEOUT = 10  # Seconds


# Parsing helper functions
def coerce_to_string(val):
    if isinstance(val, str):
        return val
    elif isinstance(val, int):
        return str(val)
    elif isinstance(val, bytes):
        return val.decode('utf-8')
    else:
        raise TypeError(
            "Input {0} is not a string or integer, and it needs to be!".format(
                val))


def coerce_string_to_ascii(val):
    if isinstance(val, str):
        return val.encode('ascii')
    elif isinstance(val, bytes):
        return val
    else:
        raise TypeError(
            "Input {0} is not a string, string expected".format(val))


def coerce_http_method(val):
    myval = val
    if not isinstance(myval, str) or len(val) == 0:
        raise TypeError(
            "Invalid HTTP method name: input {0} is not a string or has 0 length".format(
                val))
    if isinstance(myval, bytes):
        myval = myval.decode('utf-8')
    return myval.upper()


def coerce_list_of_ints(val):
    """ If single value, try to parse as integer, else try to parse as list of integer """
    if isinstance(val, list):
        return [int(x) for x in val]
    else:
        return [int(val)]


class HttpTestResult(TestResult):
    """ Encapsulates everything about a test response """
    test = None  # Test run
    response_code = None

    body = None  # Response body, if tracked

    passed = False
    response_headers = None
    failures = None

    def __init__(self):
        self.failures = list()

    def __str__(self):
        msg = list()
        msg.append("\n====================")
        msg.append("Test Type: {}".format(self.test.test_type))
        msg.append("Passed? : {}".format(self.passed))
        msg.append("Test Url: {} {}".format(self.test.method, self.test.url))
        msg.append("Response Code: {}".format(self.response_code))
        msg.append("Response Headers: {}".format(self.response_headers))
        msg.append("Response Body: {}".format(self.body))
        msg.append("Failures : {}".format(self.failures))
        msg.append("====================\n")

        return "\n".join(msg)


def parse_headers(header_string):
    """ Parse a header-string into individual headers
        Implementation based on: http://stackoverflow.com/a/5955949/95122
        Note that headers are a list of (key, value) since duplicate headers are allowed

        NEW NOTE: keys & values are unicode strings, but can only contain ISO-8859-1 characters
    """
    # First line is request line, strip it out
    if not header_string:
        return list()
    request, headers = header_string.split('\r\n', 1)
    if not headers:
        return list()

    header_msg = message_from_string(headers)
    # Note: HTTP headers are *case-insensitive* per RFC 2616
    return [(k.lower(), v) for k, v in header_msg.items()]


class HttpTest(object):
    """ Describes a REST test """
    test_type = "http_test"
    url = None
    expected_status = [200]  # expected HTTP status code or codes
    http_body = None
    http_headers = dict()  # HTTP Headers
    method = 'GET'
    group = 'Default'
    name = 'Unnamed'
    validators = None  # Validators for response body, IE regexes, etc
    stop_on_failure = True
    failures = None
    auth_username = None
    auth_password = None
    auth_type = HttpAuthType.HTTP_AUTH_BASIC
    delay = 0

    templates = None  # Dictionary of template to compiled template

    # Bind variables, generators, and contexts
    variable_binds = None
    generator_binds = None  # Dict of variable name and then generator name
    extract_binds = None  # Dict of variable name and extract function to run
    context = None

    def __init__(self):
        self.headers = dict()
        self.expected_status = [200]
        self.http_client = None
        self.http_handler = None

    @staticmethod
    def has_contains():
        return 'contains' in validators.VALIDATORS

    def ninja_copy(self):
        """ Optimization: limited copy of test object, for realize() methods
            This only copies fields changed vs. class, and keeps methods the same
        """
        output = HttpTest()
        myvars = vars(self)
        output.__dict__ = myvars.copy()
        return output

    # These are variables that can be templated
    def set_body(self, value):
        """ Set body, directly """
        self.http_body = value

    def get_body(self, context=None):
        """ Read body from file, applying template if pertinent """
        if self.http_body is None:
            return None
        elif isinstance(self.http_body, str):
            return self.http_body
        else:
            return self.http_body.get_content(context=context)

    body = property(get_body, set_body, None,
                    'Request body, if any (for POST/PUT methods)')

    def set_context(self, context=None):
        self.context = context

    NAME_HEADERS = 'headers'

    def set_headers(self, value):
        self.http_headers = value

    def get_headers(self, context=None):
        """ Get headers, applying template if pertinent """
        if not context:
            context = self.context
        if not context:
            return self.http_headers

        vals = context.get_values()

        def template_tuple(tuple_input):
            return (string.Template(str(tuple_item)).safe_substitute(vals)
                    for tuple_item in tuple_input)

        return dict(map(template_tuple, self.http_headers.items()))

    headers = property(get_headers, set_headers, None,
                       'Headers dictionary for request')

    def update_context_before(self):
        """ Make pre-test context updates, by applying variable and generator updates """
        context = self.context
        if self.variable_binds:
            context.bind_variables(self.variable_binds)
        if self.generator_binds:
            for key, value in self.generator_binds.items():
                context.bind_generator_next(key, value)

    def update_context_after(self, response_body, headers):
        """ Run the extraction routines to update variables based on HTTP response body """
        context = self.context
        if self.extract_binds:
            for key, value in self.extract_binds.items():
                result = value.extract(
                    body=response_body, headers=headers, context=context)
                context.bind_variable(key, result)

    def __str__(self):
        return json.dumps(self, default=safe_to_json)

    def realize(self, context=None):
        if not context:
            context = self.context
        if self.url.startswith('/'):
            self.url = "$default_base_url" + self.url
        self.url = templated_var(self.url, context)
        self.method = templated_var(self.method, context)
        self.body = templated_var(self.body, context)
        self.headers = templated_var(self.headers, context)

    def send_request(self, timeout=DEFAULT_TIMEOUT, context=None,
                     handler=None, ssl_insecure=True, verbose=False):
        if not context:
            context = self.context
        self.realize(context)
        self.http_client = HttpClient(handler)
        self.http_handler = self.http_client.get_handler()
        return self.http_client.send_request(
            test_obj=self,
            timeout=timeout,
            context=context,
            ssl_insecure=ssl_insecure,
            verbose=verbose
        )

    @classmethod
    def parse_from_dict(cls, node, input_test=None, test_path=None):
        """ Create or modify a test, input_test, using configuration in node, and base_url
        If no input_test is given, creates a new one

        Test_path gives path to test file, used for setting working directory in setting up input bodies

        Uses explicitly specified elements from the test input structure
        to make life *extra* fun, we need to handle list <-- > dict transformations.

        This is to say: list(dict(),dict()) or dict(key,value) -->  dict() for some elements

        Accepted structure must be a single dictionary of key-value pairs for test configuration """

        mytest = input_test
        if not mytest:
            mytest = HttpTest()

        # Clean up for easy parsing
        node = lowercase_keys(flatten_dictionaries(node))

        # Simple table of variable name, coerce function, and optionally special store function
        CONFIG_ELEMENTS = {
            # Simple variables
            u'auth_username': [coerce_string_to_ascii],
            u'auth_password': [coerce_string_to_ascii],
            u'method': [coerce_http_method],  # HTTP METHOD
            u'delay': [lambda x: int(x)],  # Delay before running
            u'group': [coerce_to_string],  # Test group name
            u'name': [coerce_to_string],  # Test name
            u'expected_status': [coerce_list_of_ints],
            u'stop_on_failure': [safe_to_bool],

            # Templated / special handling
            # u'body': [ContentHandler.parse_content]

            # COMPLEX PARSE OPTIONS
            # u'extract_binds':[],  # Context variable-to-extractor output binding
            # u'variable_binds': [],  # Context variable to value binding
            # u'generator_binds': [],  # Context variable to generator output binding
            # u'validators': [],  # Validation functions to run
        }

        def use_config_parser(configobject, configelement, configvalue):
            """ Try to use parser bindings to find an option for parsing and storing config element
                :configobject: Object to store configuration
                :configelement: Configuratione element name
                :configvalue: Value to use to set configuration
                :returns: True if found match for config element, False if didn't
            """

            myparsing = CONFIG_ELEMENTS.get(configelement)
            if myparsing:
                converted = myparsing[0](configvalue)
                setattr(configobject, configelement, converted)
                return True
            return False

        # Copy/convert input elements into appropriate form for a test object
        for configelement, configvalue in node.items():
            if use_config_parser(mytest, configelement, configvalue):
                continue

            # Configure test using configuration elements
            if configelement == 'url':
                if isinstance(configvalue, dict):
                    configvalue = configvalue.get("template")
                mytest.url = coerce_to_string(configvalue)
            elif configelement == 'body':
                if isinstance(configvalue, dict):
                    configvalue = configvalue.get("template")
                mytest.http_body = configvalue
            elif configelement == 'extract_binds':
                # Add a list of extractors, of format:
                # {variable_name: {extractor_type: extractor_config}, ... }
                binds = flatten_dictionaries(configvalue)
                if mytest.extract_binds is None:
                    mytest.extract_binds = dict()

                for variable_name, extractor in binds.items():
                    if not isinstance(extractor, dict) or len(
                            extractor) == 0:
                        raise TypeError(
                            "Extractors must be defined as maps of extractorType:{configs} with 1 entry")
                    if len(extractor) > 1:
                        raise ValueError(
                            "Cannot define multiple extractors for given variable name")

                    # Safe because length can only be 1
                    for extractor_type, extractor_config in extractor.items():
                        mytest.extract_binds[
                            variable_name] = validators.parse_extractor(
                            extractor_type, extractor_config)

            elif configelement == 'validators':
                # Add a list of validators
                if not isinstance(configvalue, list):
                    raise Exception(
                        'Misconfigured validator section, must be a list of validators')
                if mytest.validators is None:
                    mytest.validators = list()

                # create validator and add to list of validators
                for var in configvalue:
                    if not isinstance(var, dict):
                        raise TypeError(
                            "Validators must be defined as validatorType:{configs} ")
                    for validator_type, validator_config in var.items():
                        validator = validators.parse_validator(
                            validator_type, validator_config)
                        mytest.validators.append(validator)

            elif configelement == 'headers':  # HTTP headers to use, flattened to a single string-string dictionary
                configvalue = flatten_dictionaries(configvalue)
                if isinstance(configvalue, dict):
                    mytest.headers = configvalue
                elif isinstance(configvalue, str):
                    try:
                        mytest.headers = json.loads(configvalue)
                    except Exception as e:
                        logger.error(str(e))
                        raise Exception("header must be dict or json str")
                else:
                    raise TypeError(
                        "Illegal header type: headers must be a dictionary or list of dictionary keys")
            elif configelement == 'variable_binds':
                mytest.variable_binds = flatten_dictionaries(configvalue)
            elif configelement == 'generator_binds':
                output = flatten_dictionaries(configvalue)
                output2 = dict()
                for key, value in output.items():
                    output2[str(key)] = str(value)
                mytest.generator_binds = output2

        # For non-GET requests, accept additional response codes indicating success
        # (but only if not expected statuses are not explicitly specified)
        # this is per HTTP spec:
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.5
        if 'expected_status' not in node.keys():
            if mytest.method == 'POST':
                mytest.expected_status = [200, 201, 204]
            elif mytest.method == 'PUT':
                mytest.expected_status = [200, 201, 204]
            elif mytest.method == 'DELETE':
                mytest.expected_status = [200, 202, 204]
            # Fallthrough default is simply [200]
        return mytest
