import json


class TestResult:
    """ Encapsulates everything about a test response """
    test_type = None
    test = None  # Test run
    passed = False
    failures = None

    def __init__(self):
        self.failures = list()

    def __str__(self):
        msg = list()
        msg.append("\n====================")
        msg.append("Test Type: {}".format(self.test.test_type))
        msg.append("Passed? : {}".format(self.passed))
        msg.append("Failures : {}".format(self.failures))
        msg.append("====================\n")

        return "\n".join(msg)