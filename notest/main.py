#!/usr/bin/env python
import sys
import os
import json
import logging
from optparse import OptionParser
from notest.lib.utils import read_test_file

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))

from notest.notest_lib import notest_run
from notest.test_result import TestResultsAnalyzer, show_total_results


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

DEFAULT_LOGGING_LEVEL = logging.INFO

logger = logging.getLogger('notest.main')
logging_config = {
    'level': DEFAULT_LOGGING_LEVEL,
    'format': "%(asctime)s - %(levelname)s - %(message)s"
}


def main(args):
    """
    Execute a test against the given base url.

    Keys allowed for args:
        test_file          - REQUIRED - Test file (yaml)
        log           - OPTIONAL - set logging level {debug,info,warning,error,critical} (default=warning)
        interactive   - OPTIONAL - mode that prints info before and after test exectuion and pauses for user input for each test
        config_file
        ssl_insecure
        ext_dir
        default_base_url
        request_client
        loop_interval

    """

    if 'log' in args and args['log'] is not None:
        level = LOGGING_LEVELS.get(args['log'].lower())
        logging_config['level'] = level
    logging.basicConfig(**logging_config)

    test_file = args['test_file']
    test_structure = read_test_file(test_file)

    args['test_structure'] = test_structure
    args['working_directory'] = os.path.dirname(test_file)

    # Execute all testsets
    total_results = notest_run(args)
    show_total_results(total_results)
    analyzer = TestResultsAnalyzer(total_results)
    if analyzer.get_failed_cases_count() > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def parse_command_line_args(args_in):
    """ Runs everything needed to execute from the command line, so main method is callable without arg parsing """
    parser = OptionParser(
        usage="usage: notest test_filen.yaml [options] ")
    parser.add_option("--log", help="Logging level",
                      action="store", type="string")
    parser.add_option("-i", "--interactive", help="Interactive mode",
                      action="store_true", dest="interactive", default=False)
    parser.add_option("-t", "--test-file", help="Test file to use, yaml or json file",
                      action="store", type="string",
                      dest="test_file")
    parser.add_option('--ssl-insecure',
                      help='Disable cURL host and peer cert verification',
                      action='store_true', default=False,
                      dest="ssl_insecure")
    parser.add_option('--ext-dir',
                      help='local extensions dir, default ./ext',
                      action='store',
                      dest="ext_dir")
    parser.add_option('--env-vars',
                      help='environment variables, format: json, will be injected to config-variable-binds of testset',
                      action='store',
                      dest="env_vars")
    parser.add_option('--env-file',
                      help='environment variables file, will be injected to config-variable-binds of testset',
                      action='store',
                      dest="env_file")
    parser.add_option("-b", '--default-base-url',
                      help='default base url, if not specified, use the config in test file',
                      action='store',
                      dest="default_base_url")
    parser.add_option("-c", '--config-file',
                      help='config file',
                      action='store',
                      dest="config_file")
    parser.add_option("-l", '--loop-interval',
                      help='loop_interval, default 2s',
                      action='store',
                      dest="loop_interval")
    parser.add_option("-r", '--request-client',
                      help='request_client, select one in [requests, pycurl], default requests. '
                           'If use pycurl, you should install pycurl first by "pip install -U pycurl"',
                      action='store',
                      dest="request_client")
    parser.add_option('--libcurl-path',
                      help='pycurl request_client need libcurl installed in os',
                      action='store',
                      dest="libcurl_path")
    parser.add_option('--libcurl-ca-file',
                      help='pycurl request_client need libcurl ca/cert file specified in win os',
                      action='store',
                      dest="libcurl_ca_file")
    parser.add_option("-v", '--override-config-variable-binds',
                      help='override_config_variable_binds, format -o key1=value1 -o key2=value2',
                      action='append',
                      dest="override_config_variable_binds")

    (args, unparsed_args) = parser.parse_args(args_in)
    args = vars(args)

    # Handle url/test as named, or, failing that, positional arguments
    if not args['test_file']:
        if len(unparsed_args) > 0:
            args['test_file'] = unparsed_args[0]
        else:
            parser.print_help()
            parser.error(
                "wrong number of arguments, need test filename, either as 1st parameters or via --test")

    # So modules can be loaded from current folder
    args['cwd'] = os.path.realpath(os.path.abspath(os.getcwd()))
    return args


def command_line_run():
    args_in = sys.argv[1:]
    args = parse_command_line_args(args_in)
    main(args)


# Allow import into another module without executing the main method
if __name__ == '__main__':
    command_line_run()
