# Sample python extension
import notest.validators as validators
from notest.context import Context
from notest.lib.utils import templated_var
import sys


'''
- operation:
    - type: "print_operation"
    - print: 'hello world'
'''


def print_operation(config, context=None):
    print("Run print_operation")
    assert isinstance(config, dict)
    assert "print" in config
    pr = config['print']
    pr = templated_var(pr, context)
    print(pr)
    print('')


class ContainsValidator(validators.AbstractValidator):
    # Sample validator that verifies a string is contained in the request body
    contains_string = None

    def validate(self, body=None, headers=None, context=None):
        if isinstance(body, bytes) and isinstance(self.contains_string, str):
            result = self.contains_string.encode('utf-8') in body
        else:
            result = self.contains_string in body
        if result:
            return True
        else:  # Return failure object with additional information
            message = "Request body did not contain string: {0}".format(
                self.contains_string)
            return validators.Failure(message=message, details=None, validator=self)

    @staticmethod
    def parse(config):
        """ Parse a contains validator, which takes as the config a simple string to find """
        if not isinstance(config, str):
            raise TypeError("Contains input must be a simple string")
        validator = ContainsValidator()
        validator.contains_string = config
        return validator


class WeirdzoExtractor(validators.AbstractExtractor):
    """ Always returns 'zorba' """

    extractor_type = 'weirdzo'
    is_body_extractor = True

    @classmethod
    def parse(cls, config):
        base = WeirdzoExtractor()
        base.query = config.get('query')
        return base

    def extract_internal(self, body=None, headers=None, context=None):
        return 'zorba'


def parse_generator_doubling(config):
    """ Returns generators that double with each value returned
        Config includes optional start value """
    start = 1
    if 'start' in config:
        start = int(config['start'])

    # We cannot simply use start as the variable, because of scoping
    # limitations
    def generator():
        val = start
        while(True):
            yield val
            val = val * 2
    return generator()


def test_is_dict(input):
    """ Simple test that returns true if item is a dictionary """
    return isinstance(input, dict)


OPERATIONS = {'print_operation': print_operation}
# This is where the magic happens, each one of these is a registry of
# validators/extractors/generators to use
VALIDATORS = {'contains': ContainsValidator.parse}
VALIDATOR_TESTS = {'is_dict': test_is_dict}

# Converts to lowercase and tests for equality
COMPARATORS = {'str.eq.lower': lambda a, b: str(a).lower() == str(b).lower()}

EXTRACTORS = {'weirdzo': WeirdzoExtractor.parse}
GENERATORS = {'doubling': parse_generator_doubling}
