#!/usr/bin/env python
import sys
import os
import inspect
import traceback
import yaml
import json
import logging
import threading
from optparse import OptionParser
from email import message_from_string  # For headers handling
import time

from pyresttest.clients.http_client import HttpClient
from pyresttest.plugin_registery import register_extensions
from pyresttest.lib.utils import templated_var

ESCAPE_DECODING = 'unicode_escape'

# Dirty hack to allow for running this as a script :-/
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(
        os.path.realpath(__file__))))
    from pyresttest.context import Context
    from pyresttest import generators
    from pyresttest import validators
    from pyresttest import tests
    from pyresttest.generators import parse_generator
    from pyresttest.parsing import flatten_dictionaries, lowercase_keys, \
        safe_to_bool, safe_to_json

    from pyresttest.validators import Failure
    from pyresttest.tests import Test, DEFAULT_TIMEOUT

else:  # Normal imports
    # Pyresttest internals
    from . import context
    from .context import Context
    from . import generators
    from .generators import parse_generator
    from . import parsing
    from .parsing import flatten_dictionaries, lowercase_keys, safe_to_bool, \
        safe_to_json
    from . import validators
    from .validators import Failure
    from . import tests
    from .tests import Test, DEFAULT_TIMEOUT

"""
Executable class, ties everything together into the framework.
Module responsibilities:
- Read & import test test_files
- Parse test configs
- Provide executor methods for sets of tests and benchmarks
- Collect and report on test/benchmark results
- Perform analysis on benchmark results
"""
HEADER_ENCODING = 'ISO-8859-1'  # Per RFC 2616
LOGGING_LEVELS = {'debug': logging.DEBUG,
                  'info': logging.INFO,
                  'warning': logging.WARNING,
                  'error': logging.ERROR,
                  'critical': logging.CRITICAL}

logging.basicConfig(format='%(levelname)s:%(message)s')
logger = logging.getLogger('pyresttest.main')

DIR_LOCK = threading.RLock()  # Guards operations changing the working directory


class cd:
    """Context manager for changing the current working directory"""

    # http://stackoverflow.com/questions/431684/how-do-i-cd-in-python/13197763#13197763

    def __init__(self, newPath):
        self.newPath = newPath

    def __enter__(self):
        if self.newPath:  # Don't CD to nothingness
            DIR_LOCK.acquire()
            self.savedPath = os.getcwd()
            os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        if self.newPath:  # Don't CD to nothingness            
            os.chdir(self.savedPath)
            DIR_LOCK.release()


class TestConfig:
    """ Configuration for a test run """
    timeout = DEFAULT_TIMEOUT  # timeout of tests, in seconds
    print_bodies = False  # Print response bodies in all cases
    print_headers = False  # Print response bodies in all cases
    retries = 0  # Retries on failures
    test_parallel = False  # Allow parallel execution of tests in a test set, for speed?
    interactive = False
    verbose = False
    ssl_insecure = False
    skip_term_colors = False  # Turn off output term colors

    # Binding and creation of generators
    variable_binds = None
    generators = None  # Map of generator name to generator function

    def __str__(self):
        return json.dumps(self, default=safe_to_json)


class TestSet:
    """ Encapsulates a set of tests and test configuration for them """
    tests = list()
    config = TestConfig()

    def __init__(self):
        self.config = TestConfig()
        self.tests = list()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)


class TestResponse:
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
        return json.dumps(self, default=safe_to_json)


def read_test_file(path):
    """ Read test file at 'path' in YAML """
    # TODO allow use of safe_load_all to handle multiple test sets in a given
    # doc
    teststruct = yaml.safe_load(read_file(path))
    return teststruct


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


def parse_testsets(test_structure, test_files=set(),
                   working_directory=None, vars=None):
    """ Convert a Python data structure read from validated YAML to a set of structured testsets
    The data structure is assumed to be a list of dictionaries, each of which describes:
        - a tests (test structure)
        - a simple test (just a URL, and a minimal test is created)
        - or overall test configuration for this testset
        - an import (load another set of tests into this one, from a separate file)
            - For imports, these are recursive, and will use the parent config if none is present

    Note: test_files is used to track tests that import other tests, to avoid recursive loops

    This returns a list of testsets, corresponding to imported testsets and in-line multi-document sets
    """

    tests_list = list()
    test_config = TestConfig()
    testsets = list()

    if working_directory is None:
        working_directory = os.path.abspath(os.getcwd())

    if vars and isinstance(vars, dict):
        test_config.variable_binds = vars

    # returns a testconfig and collection of tests
    for node in test_structure:  # Iterate through lists of test and configuration elements
        if isinstance(node,
                      dict):  # Each config element is a miniature key-value dictionary
            node = lowercase_keys(node)
            for key in node:
                if key == u'import':
                    importfile = node[key]  # import another file
                    if importfile not in test_files:
                        logger.debug("Importing test sets: " + importfile)
                        test_files.add(importfile)
                        import_test_structure = read_test_file(importfile)
                        with cd(os.path.dirname(
                                os.path.realpath(importfile))):
                            import_testsets = parse_testsets(
                                import_test_structure, test_files,
                                vars=vars)
                            testsets.extend(import_testsets)
                elif key == u'url':  # Simple test, just a GET to a URL
                    mytest = Test()
                    val = node[key]
                    assert isinstance(val, str)
                    mytest.url = val
                    tests_list.append(mytest)
                elif key == u'test':  # Complex test with additional parameters
                    with cd(working_directory):
                        child = node[key]
                        mytest = Test.init_test(child)
                        tests_list.append(mytest)
                elif key == u'config' or key == u'configuration':
                    test_config = parse_configuration(
                        node[key], base_config=test_config)
    testset = TestSet()
    testset.tests = tests_list
    testset.config = test_config
    testsets.append(testset)
    return testsets


def parse_configuration(node, base_config=None):
    """ Parse input config to configuration information """
    test_config = base_config
    if not test_config:
        test_config = TestConfig()

    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    # ahead process variable_binds, other key can use it in template
    if not test_config.variable_binds:
        test_config.variable_binds = dict()

    if 'variable_binds' in node:
        value = node['variable_binds']
        test_config.variable_binds.update(flatten_dictionaries(value))

    # set default_base_url to global variable_binds
    if 'default_base_url' in node:
        value = node['default_base_url']
        default_base_url = templated_var(value, test_config.variable_binds)
        test_config.variable_binds['default_base_url'] = default_base_url

    for key, value in node.items():
        if key == 'timeout':
            test_config.timeout = int(value)
        elif key == 'print_bodies':
            test_config.print_bodies = safe_to_bool(value)
        elif key == 'retries':
            test_config.retries = int(value)
        elif key == 'variable_binds':
            pass
        elif key == 'generators':
            flat = flatten_dictionaries(value)
            gen_map = dict()
            for generator_name, generator_config in flat.items():
                gen = parse_generator(generator_config, test_config.variable_binds)
                gen_map[str(generator_name)] = gen
            test_config.generators = gen_map

    return test_config


def read_file(path):
    """ Read an input into a file, doing necessary conversions around relative path handling """
    with open(path, "r") as f:
        string = f.read()
        f.close()
    return string


def run_test(mytest, test_config=TestConfig(), context=None,
             http_handler=None, *args, **kwargs):
    """ Put together test pieces: configure & run actual test, return results """

    # Initialize a context if not supplied
    my_context = context
    if my_context is None:
        my_context = Context()
    mytest.context = my_context
    mytest.update_context_before()

    result = TestResponse()
    result.test = mytest
    result.passed = None

    if test_config.interactive:
        print("===================================")
        print("%s" % mytest.name)
        print("-----------------------------------")
        print("REQUEST:")
        print("%s %s" % (mytest.method, mytest.url))
        print("HEADERS:")
        print("%s" % (mytest.headers))
        if mytest.body is not None:
            print("\n%s" % mytest.body)

        input("Press ENTER when ready")

    # send request
    try:
        http_response = mytest.send_request(
            timeout=test_config.timeout,
            context=my_context,
            handler=http_handler,
            ssl_insecure=test_config.ssl_insecure,
            verbose=test_config.verbose
        )
    except Exception as e:
        # Curl exception occurred (network error), do not pass go, do not
        # collect $200
        trace = traceback.format_exc()
        result.failures.append(Failure(message="Curl Exception: {0}".format(
            e), details=trace,
            failure_type=validators.FAILURE_CURL_EXCEPTION))
        result.passed = False
        HttpClient.close_handler(http_handler)
        return result

    # Retrieve Body
    result.body = http_response.body

    # Retrieve Headers
    headers = http_response.headers
    if headers and not isinstance(headers, list):
        headers = str(headers, HEADER_ENCODING)  # Per RFC 2616
        # Parse HTTP headers
        try:
            result.response_headers = parse_headers(headers)
        except Exception as e:
            trace = traceback.format_exc()
            error = "Header parsing exception: {} {}".format(e, headers)
            result.failures.append(
                Failure(
                    message=error,
                    details=trace,
                    failure_type=validators.FAILURE_TEST_EXCEPTION))
            result.passed = False
            return result
    result.response_headers = headers
    response_code = http_response.status_code
    result.response_code = response_code

    logger.debug("Initial Test Result, based on expected response code: " +
                 str(response_code in mytest.expected_status))

    if response_code in mytest.expected_status:
        result.passed = True
    else:
        # Invalid response code
        result.passed = False
        failure_message = "Invalid HTTP response code: response code {0} not in expected codes [{1}]".format(
            response_code, mytest.expected_status)
        result.failures.append(Failure(
            message=failure_message, details=None,
            failure_type=validators.FAILURE_INVALID_RESPONSE))

    # print str(test_config.print_bodies) + ',' + str(not result.passed) + ' ,
    # ' + str(test_config.print_bodies or not result.passed)

    headers = result.response_headers

    # execute validator on body
    if result.passed is True:
        body = result.body
        if mytest.validators is not None and isinstance(mytest.validators,
                                                        list):
            logger.debug("executing this many validators: " +
                         str(len(mytest.validators)))
            failures = result.failures
            for validator in mytest.validators:
                validate_result = validator.validate(
                    body=body, headers=headers, context=my_context)
                if not validate_result:
                    result.passed = False
                # Proxy for checking if it is a Failure object, because of
                # import issues with isinstance there
                if hasattr(validate_result, 'details'):
                    failures.append(validate_result)
                # TODO add printing of validation for interactive mode
        else:
            logger.debug("no validators found")

        # Only do context updates if test was successful
        mytest.update_context_after(result.body, headers)

    # Print response body if override is set to print all *OR* if test failed
    # (to capture maybe a stack trace)
    if test_config.print_bodies or not result.passed:
        if test_config.interactive:
            print("RESPONSE:")
        if result.body:
            body = result.body
            if isinstance(body, bytes):
                print(body.decode())
            else:
                print(body)
        # else:
        #     print("None")

    if test_config.print_headers or not result.passed:
        if test_config.interactive:
            print("RESPONSE HEADERS:")
        if result.response_headers:
            print(result.response_headers)
        # else:
        #     print("None")

    # TODO add string escape on body output
    logger.debug(result)

    return result


def log_failure(failure, context=None, test_config=TestConfig()):
    """ Log a failure from a test """
    logger.error("Test Failure, failure type: {0}, Reason: {1}".format(
        failure.failure_type, failure.message))
    if failure.details:
        logger.error("Validator/Error details:" + str(failure.details))


def run_testsets(testsets):
    """ Execute a set of tests, using given TestSet list input """
    group_results = dict()  # results, by group
    group_failure_counts = dict()
    total_failures = 0
    myinteractive = False
    curl_handle = None

    for testset in testsets:
        mytests = testset.tests
        myconfig = testset.config
        context = Context()

        # Bind variables & add generators if pertinent
        if myconfig.variable_binds:
            context.bind_variables(myconfig.variable_binds)
        if myconfig.generators:
            for key, value in myconfig.generators.items():
                context.add_generator(key, value)

        # Make sure we actually have tests to execute
        if not mytests:
            # no tests in this test set, probably just imports.. skip to next
            # test set
            break

        myinteractive = True if myinteractive or myconfig.interactive else False

        # Run tests, collecting statistics as needed
        for test in mytests:
            # Initialize the dictionaries to store test fail counts and results
            if test.group not in group_results:
                group_results[test.group] = list()
                group_failure_counts[test.group] = 0

            result = run_test(test, test_config=myconfig, context=context,
                              http_handler=curl_handle)
            result.body = None  # Remove the body, save some memory!

            if not result.passed:  # Print failure, increase failure counts for that test group
                # Use result test URL to allow for templating
                error_info = list()
                error_info.append("")
                error_info.append(' Test Failed: ' + test.name)
                error_info.append(" URL=" + result.test.url)
                error_info.append(" Group=" + test.group)
                error_info.append(
                    " HTTP Status Code: " + str(result.response_code))
                error_info.append("")
                logger.error("\n".join(error_info))

                # Print test failure reasons
                if result.failures:
                    for failure in result.failures:
                        log_failure(failure, context=context,
                                    test_config=myconfig)

                # Increment test failure counts for that group (adding an entry
                # if not present)
                failures = group_failure_counts[test.group]
                failures = failures + 1
                group_failure_counts[test.group] = failures

            else:  # Test passed, print results
                msg = list()
                msg.append("")
                msg.append('Test Succeeded: ' + test.name)
                msg.append(" URL=" + result.test.url)
                msg.append(" Group=" + test.group)
                msg.append(
                    " HTTP Status Code: " + str(result.response_code))
                msg.append("")
                logger.info("\n".join(msg))

            # Add results for this test group to the resultset
            group_results[test.group].append(result)

            # handle stop_on_failure flag
            if not result.passed and test.stop_on_failure is not None and test.stop_on_failure:
                print(
                    'STOP ON FAILURE! stopping test set execution, continuing with other test sets')
                break

    if myinteractive:
        # a break for when interactive bits are complete, before summary data
        print("===================================")

    # Print summary results
    for group in sorted(group_results.keys()):
        test_count = len(group_results[group])
        failures = group_failure_counts[group]
        total_failures = total_failures + failures

        passfail = {True: u'SUCCEEDED: ', False: u'FAILED: '}
        output_string = "Test Group {0} {1}: {2}/{3} Tests Passed!".format(
            group, passfail[failures == 0], str(test_count - failures),
            str(test_count))

        if myconfig.skip_term_colors:
            print(output_string)
        else:
            if failures > 0:
                print('\033[91m' + output_string + '\033[0m')
            else:
                print('\033[92m' + output_string + '\033[0m')

    return total_failures


def main(args):
    """
    Execute a test against the given base url.

    Keys allowed for args:
        test          - REQUIRED - Test file (yaml)
        print_bodies  - OPTIONAL - print response body
        print_headers  - OPTIONAL - print response headers
        log           - OPTIONAL - set logging level {debug,info,warning,error,critical} (default=warning)
        interactive   - OPTIONAL - mode that prints info before and after test exectuion and pauses for user input for each test
        absolute_urls - OPTIONAL - mode that treats URLs in tests as absolute/full URLs instead of relative URLs
        skip_term_colors - OPTIONAL - mode that turn off the output term colors
    """

    if 'log' in args and args['log'] is not None:
        logger.setLevel(LOGGING_LEVELS.get(
            args['log'].lower(), logging.NOTSET))

    if 'import_extensions' in args and args['import_extensions']:
        extensions = args['import_extensions'].split(';')

        # We need to add current folder to working path to import modules
        working_folder = args['cwd']
        if working_folder not in sys.path:
            sys.path.insert(0, working_folder)
        register_extensions(extensions)

    test_file = args['test']
    test_structure = read_test_file(test_file)

    my_vars = None
    if 'vars' in args and args['vars'] is not None:
        my_vars = yaml.safe_load(args['vars'])
    if my_vars and not isinstance(my_vars, dict):
        raise Exception("Variables must be a dictionary!")

    tests = parse_testsets(test_structure,
                           working_directory=os.path.dirname(test_file),
                           vars=my_vars)

    # Override configs from command line if config set
    for t in tests:
        if 'print_bodies' in args and args[
            'print_bodies'] is not None and bool(args['print_bodies']):
            t.config.print_bodies = safe_to_bool(args['print_bodies'])

        if 'print_headers' in args and args[
            'print_headers'] is not None and bool(args['print_headers']):
            t.config.print_headers = safe_to_bool(args['print_headers'])

        if 'interactive' in args and args['interactive'] is not None:
            t.config.interactive = safe_to_bool(args['interactive'])

        if 'verbose' in args and args['verbose'] is not None:
            t.config.verbose = safe_to_bool(args['verbose'])

        if 'ssl_insecure' in args and args['ssl_insecure'] is not None:
            t.config.ssl_insecure = safe_to_bool(args['ssl_insecure'])

        if 'skip_term_colors' in args and args[
            'skip_term_colors'] is not None:
            t.config.skip_term_colors = safe_to_bool(
                args['skip_term_colors'])

    # Execute all testsets
    failures = run_testsets(tests)

    sys.exit(failures)


def parse_command_line_args(args_in):
    """ Runs everything needed to execute from the command line, so main method is callable without arg parsing """
    parser = OptionParser(
        usage="usage: %prog base_url test_filename.yaml [options] ")
    parser.add_option(u"--print-bodies", help="Print all response bodies",
                      action="store", type="string", dest="print_bodies")
    parser.add_option(u"--print-headers", help="Print all response headers",
                      action="store", type="string", dest="print_headers")
    parser.add_option(u"--log", help="Logging level",
                      action="store", type="string")
    parser.add_option(u"--interactive", help="Interactive mode",
                      action="store", type="string")
    parser.add_option(u"--test", help="Test file to use",
                      action="store", type="string")
    parser.add_option(u'--import_extensions',
                      help='Extensions to import, separated by semicolons',
                      action="store", type="string")
    parser.add_option(
        u'--vars', help='Variables to set, as a YAML dictionary',
        action="store", type="string")
    parser.add_option(u'--verbose',
                      help='Put cURL into verbose mode for extra debugging power',
                      action='store_true', default=False, dest="verbose")
    parser.add_option(u'--ssl-insecure',
                      help='Disable cURL host and peer cert verification',
                      action='store_true', default=False,
                      dest="ssl_insecure")
    parser.add_option(u'--skip_term_colors',
                      help='Turn off the output term colors',
                      action='store_true', default=False,
                      dest="skip_term_colors")

    (args, unparsed_args) = parser.parse_args(args_in)
    args = vars(args)

    # Handle url/test as named, or, failing that, positional arguments
    if not args['test']:
        if len(unparsed_args) > 0:
            args['test'] = unparsed_args[0]
        else:
            parser.print_help()
            parser.error(
                "wrong number of arguments, need test filename, either as 1st parameters or via --test")

    # So modules can be loaded from current folder
    args['cwd'] = os.path.realpath(os.path.abspath(os.getcwd()))
    return args


def command_line_run(args_in):
    args = parse_command_line_args(args_in)
    main(args)


# Allow import into another module without executing the main method
if (__name__ == '__main__'):
    command_line_run(sys.argv[1:])
