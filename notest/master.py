#!/usr/bin/env python
import sys
import os
import time
import logging
import threading
from notest.lib.utils import templated_var
from notest.lib.utils import read_test_file
from notest.operations import get_operation_function
from notest.test_result import TestResult
from notest.testset import TestSet, TestSetConfig


ESCAPE_DECODING = 'unicode_escape'

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
from notest.context import Context
from notest.generators import parse_generator
from notest.operations import Operation
from notest.lib.parsing import flatten_dictionaries, lowercase_keys
from notest.test_runners import get_test_runner_parser


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


def parse_configuration(node, base_config=None):
    """ Parse input config to configuration information """
    test_config = base_config
    if not test_config:
        test_config = TestSetConfig()

    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    if "testset" in node:
        test_config.testset_name = node['testset']

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
        elif key == 'retries':
            test_config.retries = int(value)
        elif key == 'collect_import_result':
            if isinstance(value, str):
                value = True if value.lower() == 'true' else False
            test_config.collect_import_result = value
        elif key == 'variable_binds':
            pass
        elif key == 'request_client':
            test_config.request_client = str(value)
        elif key == 'generators':
            flat = flatten_dictionaries(value)
            gen_map = dict()
            for generator_name, generator_config in flat.items():
                gen = parse_generator(
                    configuration=generator_config,
                    variable_binds={
                        **test_config.variable_binds,
                        'working_directory': test_config.working_directory
                    })
                gen_map[str(generator_name)] = gen
            test_config.generators = gen_map

    if 'data_driven' in node:
        value = node['data_driven']
        generator_name = value.get('generator', None)
        generator_obj = test_config.generators[generator_name]
        test_config.data_driven_generator = generator_obj
        test_config.data_driven_generator_name = generator_name

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
    test_config = TestSetConfig()
    testsets = list()

    if working_directory is None:
        working_directory = os.path.abspath(os.getcwd())
    test_config.working_directory = working_directory

    # returns a testconfig and collection of testsets
    assert isinstance(test_structure, list)

    testset = TestSet()

    index = 0
    while index < len(test_structure):  # Iterate through lists of test and configuration elements
        node = test_structure[index]
        if isinstance(node, dict):  # Each config element is a miniature key-value dictionary
            node = lowercase_keys(node)
            for key in node:
                if key == 'include':
                    includefile = node[key]  # include another file as module/modules
                    if includefile[0] != "/":
                        includefile = os.path.join(working_directory,
                                                   includefile)
                    # load include module file and delete its config, add its test/operation to local flow
                    subnodes = read_test_file(includefile)
                    assert isinstance(subnodes, list)
                    i = index + 1
                    for sn in subnodes:
                        keys = sn.keys()
                        assert len(keys) == 1
                        if list(keys)[0] in ['config']:
                            continue
                        test_structure.insert(i, sn)
                        i += 1

                if key == 'import':   # import another testset file
                    if isinstance(node[key], dict):
                        importfile = node[key]['file']
                        input = node[key].get('input')
                        extract = node[key].get('extract')
                    elif isinstance(node[key], str):
                        importfile = node[key]
                        input = None
                        extract = None
                    else:
                        raise Exception("Wrong Import Format: {}".format(node[key]))

                    if importfile[0] != "/":
                        importfile = os.path.join(working_directory,
                                                  importfile)
                    if importfile not in test_files:
                        logger.info("Importing test sets: " + importfile)
                        test_files.add(importfile)
                        import_test_structure = read_test_file(importfile)
                        with CD(os.path.dirname(
                                os.path.realpath(importfile))):
                            try:
                                import_testsets = parse_testsets(
                                    import_test_structure, test_files)
                            except Exception as e:
                                error_info = "Import SubTestSet {} ERROR, msg: {}".format(importfile, str(e))
                                logger.error(error_info)
                                raise Exception(error_info)
                            assert len(import_testsets) == 1
                            import_testsets[0].config.extract = extract
                            testset.subtestsets[importfile] = import_testsets[0]

                            subtestset = TestSet()
                            subtestset.input = input
                            subtestset.extract = extract
                            subtestset.file_path = importfile
                            tests_list.append(subtestset)  # call sub testset is also a test step

                # elif key == 'url':  # Simple test, just a GET to a URL
                #     mytest = HttpTest()
                #     val = node[key]
                #     assert isinstance(val, str)
                #     mytest.url = val
                #     tests_list.append(mytest)
                elif key == 'test':  # Complex test with additional parameters
                    with CD(working_directory):
                        child = node[key]
                        test_type = child.get('test_type', 'http_test')
                        # mytest = HttpTest.parse_from_dict(child)
                        runner_parser_func = get_test_runner_parser(test_type)
                        mytest = runner_parser_func(child)
                        mytest.original_node = child
                        tests_list.append(mytest)
                elif key == 'operation':  # Complex test with additional parameters
                    operation = Operation()
                    operation.config = flatten_dictionaries(node[key])
                    tests_list.append(operation)
                elif key == 'config' or key == 'configuration':
                    test_config = parse_configuration(
                        node[key], base_config=test_config)

                index += 1

    testset.tests = tests_list
    testset.config = test_config
    testset.name = test_config.testset_name
    for t in tests_list:
        t.testset_config = test_config
    testsets.append(testset)
    return testsets


def log_failure(failure, context=None, test_config=TestSetConfig()):
    """ Log a failure from a test """
    logger.error("Test Failure, failure type: {0}, Reason: {1}".format(
        failure.failure_type, failure.message))
    if failure.details:
        logger.error("Validator/Error details:" + str(failure.details))


def run_testset(testset, request_handle=None, test_results=None):
    mytests = testset.tests
    myconfig = testset.config
    context = Context()

    if test_results is None:
        test_results = list()

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
        return

    def none_generator():
        yield None

    data_driven_generator = None
    if myconfig.data_driven_generator:
        data_driven_generator = myconfig.data_driven_generator
    else:
        data_driven_generator = none_generator()

    for ddt_data in data_driven_generator:
        if ddt_data:
            if not isinstance(ddt_data, dict):
                raise Exception("Data Driven Generator must return a dict, not {}".format(type(ddt_data)))
            logger.info("*************************")
            logger.info("Data Driven: {}".format(ddt_data))
            context.bind_variables(ddt_data)

        # Run tests, collecting statistics as needed
        index = 0
        loop_count = 0

        while index < len(mytests) and loop_count < 100:
            test = mytests[index]
            if hasattr(test.testset_config, "loop_interval"):
                loop_interval = test.testset_config.loop_interval
            else:
                loop_interval = 2

            result = None

            if test.test_type == "operation":
                logger.info("do operation {}, config:{}".format(
                    test.config.get('type'),
                    test.config
                ))
                result = TestResult()
                # result.test_type = "operation"
                result.testset_name = testset.name
                result.test_obj = test
                try:
                    opt_name = test.config.get('type')
                    opt_func = get_operation_function(opt_name)
                    opt_func(test.config, context)
                    result.passed = True
                except Exception as e:
                    result.passed = False
                test_results.append(result)

            elif test.test_type == "testset":
                logger.info("call subtestset {}".format(test.file_path))
                file_path = test.file_path
                input = test.input
                extract = test.extract
                subtestset = testset.subtestsets.get(file_path)
                result = TestResult()
                # result.test_type = "testset"
                result.test_obj = test
                result.testset_name = testset.name
                if subtestset:
                    input = templated_var(input, context)
                    if input:
                        if not subtestset.config.variable_binds:
                            subtestset.config.variable_binds = input
                        else:
                            subtestset.config.variable_binds.update(input)
                    if myconfig.collect_import_result is True:
                        sub_test_results_list = test_results
                    else:
                        sub_test_results_list = None
                    _, extract_data = run_testset(
                        subtestset, request_handle, test_results=sub_test_results_list)
                    if extract_data:
                        context.variables.update(extract_data)
                    result.passed = True
                else:
                    result.passed = False
                test_results.append(result)

            else:
                logger.debug("Run {}".format(test.test_type))
                test.reload()
                result = test.run_test(test_config=myconfig, context=context,
                                       handler=request_handle)

                result.testset_name = testset.name
                result.data_driven_fields = ddt_data
                result.test_obj = test

                if not result.passed:  # Print failure, increase failure counts for that test group
                    error_info = result.to_str(verbose=True)
                    logger.error(error_info)

                    # Print test failure reasons
                    if result.failures:
                        for failure in result.failures:
                            log_failure(failure, context=context,
                                        test_config=myconfig)

                else:  # Test passed, print results
                    logger.info(result.to_str(verbose=False))

                # Add results to the resultset
                if result.loop is False:
                    test_results.append(result)

                # handle stop_on_failure flag
                if not result.passed and test.stop_on_failure is not None and test.stop_on_failure:
                    logger.info(
                        'STOP ON FAILURE! stopping test set execution, continuing with other test sets')
                    break

            if result and result.loop is True:
                loop_count += 1
                time.sleep(loop_interval)
                continue
            else:
                index += 1
                continue

    extract_data = dict()
    if testset.config.extract:
        for key in testset.config.extract:
            if key in context.variables:
                extract_data[key] = context.variables.get(key)
            else:
                raise Exception("Error Extract Var {} in Context".format(key))

    return test_results, extract_data


def run_testsets(testsets):
    """ Execute a set of tests, using given TestSet list input """
    request_handle = None
    total_results = list()

    for testset in testsets:
        run_testset(testset, request_handle=request_handle, test_results=total_results)

    return total_results



