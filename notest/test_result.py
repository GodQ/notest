import json
import copy


class TestResult:
    """ Encapsulates everything about a test response """
    testset_name = None
    test_name = None
    test_type = None
    group = "default"
    data_driven_fields = None
    ref_test_obj = None  # Test run obj
    passed = False
    failures = None
    loop = False
    key_fields = dict()   # key fields such as url for http request
    verbose_fields = dict()   # verbose fields such as headers for http request

    def __init__(self):
        self.failures = list()

    def add_key_field(self, key, value):
        self.key_fields[key] = value

    def add_verbose_field(self, key, value):
        self.verbose_fields[key] = value

    @property
    def test_obj(self):
        return self.ref_test_obj

    @test_obj.setter
    def test_obj(self, test_obj):
        self.ref_test_obj = test_obj
        self.test_type = test_obj.test_type
        self.group = test_obj.group
        self.test_name = test_obj.name

    def __getattr__(self, attribute):
        if attribute in self.key_fields:
            return self.key_fields[attribute]
        if attribute in self.verbose_fields:
            return self.verbose_fields[attribute]

    def to_dict(self):
        d = {
            "testset": self.testset_name,
            "test_type": self.test_type,
            "test_name": self.test_name,
            "group": self.group,
            "data_driven_fields": self.data_driven_fields,
            "passed": self.passed,
            "failures": self.failures,
            **self.key_fields,
            **self.verbose_fields
        }
        return d

    def to_str(self, verbose=False):
        msg = list()
        if self.ref_test_obj:
            self.test_type = self.ref_test_obj.test_type
            self.group = self.ref_test_obj.group
            self.test_name = self.ref_test_obj.name

        msg.append("\n====================")
        if self.test_name:
            msg.append("Name: {}".format(self.test_name))
        msg.append("TestSet: {}".format(self.testset_name))
        if not self.passed:
            msg.append("Failures : {}".format(self.failures))
        for k, v in self.key_fields.items():
            msg.append("{}: {}".format(k, v))
        if verbose is True:
            msg.append("Group: {}".format(self.group))
            msg.append("Test Type: {}".format(self.test_type))
            if self.data_driven_fields:
                msg.append("Data Driven Fields: {}".format(self.data_driven_fields))
            for k, v in self.verbose_fields.items():
                msg.append("{}: {}".format(k, v))
        msg.append("Passed : {}".format(self.passed))
        msg.append("====================\n")

        return "\n".join(msg)

    def __str__(self):
        return self.to_str(verbose=True)


class TestResultsAnalyzer:
    def __init__(self, total_results):
        self.total_results = total_results
        self.test_count = len(total_results)
        self.failed_cases_count = None
        self.failed_cases = None

    def get_failed_cases_count(self):
        if self.failed_cases_count:
            return self.failed_cases_count
        else:
            self.get_failed_cases()
            return self.failed_cases_count

    def get_failed_cases(self):
        if not self.total_results:
            return None
        failed_cases = list()

        for res in self.total_results:
            if res.passed is False:
                failed_cases.append(res)
        self.failed_cases_count = len(failed_cases)
        self.failed_cases = failed_cases

        return failed_cases

    def get_cases_group_by(self, group_by):
        '''
        :param group_by:
        :return: {"group1": {"passed": [case1, case2], "failed": [case3, case4]}, "group2":.....}
        '''
        if not self.total_results:
            return None
        cases = dict()

        for res in self.total_results:
            key = getattr(res, group_by)
            if key not in cases:
                cases[key] = dict()
                cases[key]['passed'] = list()
                cases[key]['failed'] = list()

            if res.passed is False:
                cases[key]['failed'].append(res)
            else:
                cases[key]['passed'].append(res)

        return cases


def show_total_results(total_results):
    analyzer = TestResultsAnalyzer(total_results)
    cases_by_groups = analyzer.get_cases_group_by("group")

    # Print summary results
    for group in sorted(cases_by_groups.keys()):
        failed_count = len(cases_by_groups[group]["failed"])
        passed_count = len(cases_by_groups[group]["passed"])

        passfail = {True: 'SUCCEEDED: ', False: 'FAILED: '}
        output_string = "Test Group {0} {1}: {2}/{3} Tests Passed!".format(
            group, passfail[failed_count == 0], passed_count, passed_count+failed_count)

        print(output_string)