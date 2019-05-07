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
        return json.dumps(self, default=safe_to_json)