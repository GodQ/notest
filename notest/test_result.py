import json
import copy


class TestResult:
    """ Encapsulates everything about a test response """
    test_type = None
    test = None  # Test run
    passed = False
    failures = None
    loop = False

    def __init__(self):
        self.failures = list()

    def to_dict(self):
        return {}

    def __str__(self):
        msg = list()
        msg.append("\n====================")
        msg.append("Test Type: {}".format(self.test.test_type))
        msg.append("Passed? : {}".format(self.passed))
        msg.append("Failures : {}".format(self.failures))
        msg.append("====================\n")

        return "\n".join(msg)


class TotalResults:
    def __init__(self, group_results):
        self.group_results = group_results
        failure_count = 0
        sum = 0
        for group, res_list in self.group_results.items():
            for res in res_list:
                sum += 1
                if res.failures:
                    failure_count += 1
        self.failure_count = failure_count
        self.test_count = sum

    def get_failures(self, groups=None):
        if not self.group_results:
            return None
        failures = list()
        if not groups:
            groups = self.group_results.keys()

        for group in groups:
            res_list = self.group_results.get(group)
            assert res_list
            for res in res_list:
                if res.failures:
                    failures.append(res.to_dict())
        return failures
