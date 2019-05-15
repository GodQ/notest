#!/usr/bin/env python
import sys
import os
import traceback
import logging
from notest.clients.request_client import get_client_class
from notest.http_test import HttpTestResult, parse_headers, HttpTest

ESCAPE_DECODING = 'unicode_escape'

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
from notest.context import Context
from notest import validators

from notest.validators import Failure

logger = logging.getLogger('notest.http_test')


HEADER_ENCODING = 'ISO-8859-1'  # Per RFC 2616


def run_http_test(mytest, test_config, context=None,
                  http_handler=None, *args, **kwargs):
    """ Put together test pieces: configure & run actual test, return results """
    assert isinstance(mytest, HttpTest)

    # Initialize a context if not supplied
    my_context = context
    if my_context is None:
        my_context = Context()
    mytest.context = my_context
    mytest.update_context_before()

    result = HttpTestResult()
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
        client = mytest.testset_config.request_client
        if not client:
            client = "requests"
        HttpClient = get_client_class(client)
        HttpClient.close_handler(http_handler)
        return result

    # Retrieve Body
    result.body = http_response.body

    # Retrieve Headers
    headers = http_response.headers
    if headers and isinstance(headers, bytes):
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

    # execute validator
    if result.passed is True:
        body = result.body
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
        mytest.update_context_after(result.body, headers)

    # execute loop_until_conditions
    if result.passed is True:
        body = result.body
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
    logger.debug(str(result))

    return result
