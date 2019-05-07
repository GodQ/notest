#!/usr/bin/env python
import sys
import os
import yaml
import json
import logging
from optparse import OptionParser
from pyresttest.plugin_registery import register_extensions
from pyresttest.lib.utils import read_test_file
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
from pyresttest.parsing import safe_to_bool
from pyresttest.master import run_testsets, parse_testsets

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


def main(args):
    """
    Execute a test against the given base url.

    Keys allowed for args:
        test          - REQUIRED - Test file (yaml)
        log           - OPTIONAL - set logging level {debug,info,warning,error,critical} (default=warning)
        interactive   - OPTIONAL - mode that prints info before and after test exectuion and pauses for user input for each test
        skip_term_colors - OPTIONAL - mode that turn off the output term colors
    """

    if 'log' in args and args['log'] is not None:
        logger.setLevel(LOGGING_LEVELS.get(
            args['log'].lower(), logging.NOTSET))

    test_file = args['test']
    test_structure = read_test_file(test_file)

    tests = parse_testsets(test_structure,
                           working_directory=os.path.dirname(test_file))

    # Override configs from command line if config set
    for t in tests:
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
    parser.add_option("--log", help="Logging level",
                      action="store", type="string")
    parser.add_option("--interactive", help="Interactive mode",
                      action="store", type="string")
    parser.add_option("--test", help="Test file to use",
                      action="store", type="string")
    parser.add_option('--verbose',
                      help='Put cURL into verbose mode for extra debugging power',
                      action='store_true', default=False, dest="verbose")
    parser.add_option('--ssl-insecure',
                      help='Disable cURL host and peer cert verification',
                      action='store_true', default=False,
                      dest="ssl_insecure")
    parser.add_option('--skip_term_colors',
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
