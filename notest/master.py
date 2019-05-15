#!/usr/bin/env python
import sys
import os
import json
import time
import logging
import threading
from notest.lib.utils import templated_var
from notest.http_test_exec import run_http_test
from notest.lib.utils import read_test_file
from notest.operations import get_operation_function
from notest.test_result import TestResult

ESCAPE_DECODING = 'unicode_escape'

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
from notest.context import Context
from notest.generators import parse_generator
from notest.operations import Operation
from notest.lib.parsing import flatten_dictionaries, lowercase_keys, \
    safe_to_bool, safe_to_json
from notest.http_test import HttpTest, DEFAULT_TIMEOUT


"""
Executable class, ties everything together into the framework.
Module responsibilities:
- Read & import test test_files
- Parse test configs
- Provide executor methods for sets of tests and benchmarks
- Collect and report on test/benchmark results
- Perform analysis on benchmark results
"""

logger = logging.getLogger('notest.master')


DIR_LOCK = threading.RLock()  # Guards operations changing the working directory


class CD:
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
    request_client = "requests"  # requests or pycurl
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

    def set_default_base_url(self, url):
        self.variable_binds['default_base_url'] = url

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
                gen = parse_generator(generator_config,
                                      test_config.variable_binds)
                gen_map[str(generator_name)] = gen
            test_config.generators = gen_map

    return test_config


def parse_testsets(test_structure, test_files=set(), working_directory=None):
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

    # returns a testconfig and collection of tests
    for node in test_structure:  # Iterate through lists of test and configuration elements
        if isinstance(node, dict):  # Each config element is a miniature key-value dictionary
            node = lowercase_keys(node)
            for key in node:
                if key == 'import':
                    importfile = node[key]  # import another file
                    if importfile[0] != "/":
                        importfile = os.path.join(working_directory,
                                                  importfile)
                    if importfile not in test_files:
                        logger.info("Importing test sets: " + importfile)
                        test_files.add(importfile)
                        import_test_structure = read_test_file(importfile)
                        with CD(os.path.dirname(
                                os.path.realpath(importfile))):
                            import_testsets = parse_testsets(
                                import_test_structure, test_files)
                            testsets.extend(import_testsets)
                elif key == 'url':  # Simple test, just a GET to a URL
                    mytest = HttpTest()
                    val = node[key]
                    assert isinstance(val, str)
                    mytest.url = val
                    tests_list.append(mytest)
                elif key == 'test':  # Complex test with additional parameters
                    with CD(working_directory):
                        child = node[key]
                        mytest = HttpTest.parse_from_dict(child)
                        tests_list.append(mytest)
                elif key == 'operation':  # Complex test with additional parameters
                    operation = Operation()
                    operation.config = flatten_dictionaries(node[key])
                    tests_list.append(operation)
                elif key == 'config' or key == 'configuration':
                    test_config = parse_configuration(
                        node[key], base_config=test_config)

    testset = TestSet()
    testset.tests = tests_list
    testset.config = test_config
    for t in tests_list:
        t.global_config = test_config
    testsets.append(testset)
    return testsets


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
        index = 0
        while index < len(mytests):
            test = mytests[index]
            # Initialize the dictionaries to store test fail counts and results
            if test.group not in group_results:
                group_results[test.group] = list()
                group_failure_counts[test.group] = 0

            result = None
            if test.test_type == "http_test":
                result = run_http_test(test, test_config=myconfig, context=context,
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
                    msg.append('Test Name: ' + test.name)
                    msg.append("  Request= {} {}".format(result.test.method, result.test.url))
                    msg.append("  Group=" + test.group)
                    msg.append("  HTTP Status Code: {}".format(result.response_code))
                    msg.append("  passed\n")
                    logger.info("\n".join(msg))

                # Add results for this test group to the resultset
                group_results[test.group].append(result)

                # handle stop_on_failure flag
                if not result.passed and test.stop_on_failure is not None and test.stop_on_failure:
                    logger.info(
                        'STOP ON FAILURE! stopping test set execution, continuing with other test sets')
                    break
            elif test.test_type == "operation":
                logger.info("do operation {}, config:{}".format(
                    test.config.get('type'),
                    test.config
                ))
                result = TestResult()
                result.test_type = "operation"
                result.test = test
                try:
                    opt_name = test.config.get('type')
                    opt_func = get_operation_function(opt_name)
                    opt_func(test.config, context)
                    result.passed = True
                except Exception as e:
                    result.passed = False
                group_results[test.group].append(result)

            if result and result.loop is True:
                if hasattr(test.global_config, "loop_interval"):
                    loop_interval = test.global_config.loop_interval
                else:
                    loop_interval = 2
                time.sleep(loop_interval)
                continue
            else:
                index += 1
                continue

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


