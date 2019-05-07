import json
import sys

PYTHON_MAJOR_VERSION = sys.version_info[0]

import jmespath

try:  # First try to load pyresttest from global namespace
    from pyresttest import validators
    from pyresttest import context
    from pyresttest.lib import parsing
    from pyresttest import contenthandling
except ImportError:  # Then try a relative import if possible
    from .. import validators
    from .. import context
    from .. import parsing
    from .. import contenthandling


class JMESPathExtractor(validators.AbstractExtractor):
    """ Extractor that uses JMESPath syntax
        See http://jmespath.org/specification.html for details
    """
    extractor_type = 'jmespath'
    is_body_extractor = True

    def extract_internal(self, body=None, headers=None, context=None):
        mybody = body
        if PYTHON_MAJOR_VERSION > 2:
            if isinstance(mybody, bytes):
                mybody = str(mybody, 'utf-8')

        try:
            res = jmespath.search(self.query, json.loads(mybody))  # Better way
            return res
        except Exception as e:
            raise ValueError("Invalid query: " + self.query + " : " + str(e))

    @classmethod
    def parse(cls, config):
        base = JMESPathExtractor()
        base.query = config
        return base


EXTRACTORS = {'jmespath': JMESPathExtractor.parse}
