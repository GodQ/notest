#!/usr/bin/env python
import sys
import os
import traceback
import logging
from notest.clients.request_client import get_client_class
from notest.test_result import TestResult
# from notest.http_test_runner.http_test import HttpTestResult, parse_headers, HttpTest

ESCAPE_DECODING = 'unicode_escape'

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
from notest.context import Context
from notest import validators

from notest.validators import Failure

logger = logging.getLogger('notest.http_test')


HEADER_ENCODING = 'ISO-8859-1'  # Per RFC 2616


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


# class HttpTestResult(TestResult):
#     """ Encapsulates everything about a test response """
#     test_obj = None  # Test run
#     response_code = None
#
#     body = None  # Response body, if tracked
#
#     passed = False
#     response_headers = None
#     failures = None
#     loop = False
#
#     def __init__(self):
#         self.failures = list()
#
#     def to_dict(self):
#         d = {
#             "name": self.test_obj.name,
#             "test_type": self.test_obj.test_type,
#             "passed": self.passed,
#             "url": self.test_obj.url,
#             "method": self.test_obj.method,
#             "response_code": self.response_code,
#             "response_headers": self.response_headers,
#             "body": self.body,
#             "failures": list()
#         }
#         if self.failures:
#             for f in self.failures:
#                 d['failures'].append(f.to_dict())
#         return d
#
#     def __str__(self):
#         msg = list()
#         msg.append("\n====================")
#         msg.append("Test Type: {}".format(self.test_obj.test_type))
#         msg.append("Passed? : {}".format(self.passed))
#         msg.append("Test Url: {} {}".format(self.test_obj.method, self.test_obj.url))
#         msg.append("Response Code: {}".format(self.response_code))
#         msg.append("Response Headers: {}".format(self.response_headers))
#         msg.append("Response Body: {}".format(self.body))
#         msg.append("Failures : {}".format(self.failures))
#         msg.append("====================\n")
#
#         return "\n".join(msg)


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


def run_http_test(mytest, test_config, context=None, http_handler=None):
    """ Put together test pieces: configure & run actual test, return results """
    # assert isinstance(mytest, HttpTest)

    # Initialize a context if not supplied
    my_context = context
    if my_context is None:
        my_context = Context()
    mytest.context = my_context
    mytest.update_context_before()

    result = TestResult()
    result.ref_test_obj = mytest
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
        mytest.realize(my_context)
        result.add_key_field("url", mytest.url)
        result.add_key_field("method", mytest.method)
        result.add_verbose_field("request_headers", mytest.headers)
        result.add_verbose_field("request_body", mytest.body)

        http_response = mytest.send_request(
            timeout=test_config.timeout,
            context=my_context,
            handler=http_handler,
            ssl_insecure=test_config.ssl_insecure,
            verbose=test_config.verbose
        )
    except Exception as e:
        trace = traceback.format_exc()
        result.failures.append(
            Failure(message="Http Request Exception: {0}".format(e),
                    details=trace,
                    failure_type=validators.FAILURE_CURL_EXCEPTION))
        result.passed = False
        client = mytest.testset_config.request_client
        if not client:
            client = "requests"
        HttpClient = get_client_class(client)
        HttpClient.close_handler(http_handler)
        return result

    # Retrieve Body
    result.add_verbose_field('response_body', http_response.body)

    # Retrieve Headers
    headers = http_response.headers
    if headers and isinstance(headers, bytes):
        headers = str(headers, HEADER_ENCODING)  # Per RFC 2616
        # Parse HTTP headers
        try:
            result.add_verbose_field('response_headers', parse_headers(headers))
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
    elif headers and isinstance(headers, list):
        pass
    elif headers and isinstance(headers, dict):
        pass
    else:
        error = "Unknown Header Type: {}".format(type(headers))
        error_detail = "Unknown Header Type: {} {}".format(type(headers), headers)
        result.failures.append(
            Failure(
                message=error,
                details=error_detail,
                failure_type=validators.FAILURE_TEST_EXCEPTION))
        result.passed = False
        return result
    result.add_verbose_field('response_headers', headers)
    status_code = http_response.status_code
    result.add_key_field('status_code', status_code)

    logger.debug("Initial Test Result, based on expected response code: " +
                 str(status_code in mytest.expected_status))

    if status_code in mytest.expected_status:
        result.passed = True
    else:
        # Invalid response code
        result.passed = False
        failure_message = "Invalid HTTP response code: response code {0} not in expected codes [{1}]".format(
            status_code, mytest.expected_status)
        result.failures.append(Failure(
            message=failure_message, details=None,
            failure_type=validators.FAILURE_INVALID_RESPONSE))

    headers = result.response_headers

    # execute validator
    if result.passed is True:
        body = result.response_body
        if mytest.validators is not None and isinstance(mytest.validators,
                                                        list):
            logger.debug("executing validators: " +
                         str(len(mytest.validators)))
            failures = result.failures
            for validator in mytest.validators:
                validate_result = validator.validate(
                    body=body, headers=headers, context=my_context)
                if not validate_result:
                    result.passed = False
                # Proxy for checking if it is a Failure object, because of
                # import issues with isinstance there
                if isinstance(validate_result, validators.Failure):
                    failures.append(validate_result)
                # TODO add printing of validation for interactive mode
        else:
            logger.debug("no validators found")

        # Only do context updates if test was successful
        mytest.update_context_after(result.response_body, headers)

    # execute loop_until_conditions
    if result.passed is True:
        body = result.response_body
        if mytest.loop_until_conditions is not None and isinstance(mytest.loop_until_conditions, list):
            logger.debug("executing loop_until_conditions: " +
                         str(len(mytest.loop_until_conditions)))
            result.loop = False
            for validator in mytest.loop_until_conditions:
                validate_result = validator.validate(
                    body=body, headers=headers, context=my_context)
                if isinstance(validate_result, validators.Failure):
                    result.loop = True
                    logger.error(validate_result)
        else:
            logger.debug("no loop_until_conditions found")

    # Print response body if override is set to print all *OR* if test failed
    # (to capture maybe a stack trace)
    if not result.passed:
        if test_config.interactive:
            print("RESPONSE:")
            if result.response_body:
                body = result.response_body
                if isinstance(body, bytes):
                    print(body.decode())
                else:
                    print(body)

    if not result.passed:
        if test_config.interactive:
            print("RESPONSE HEADERS:")
            if result.response_headers:
                print(result.response_headers)

    # TODO add string escape on body output
    logger.debug(str(result))

    return result
