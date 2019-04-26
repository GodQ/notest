import string
import os
import copy
import json
import pycurl
import sys


from . import contenthandling
from .contenthandling import ContentHandler
from . import validators
from . import parsing
from .parsing import *

# Find the best implementation available on this platform
try:
    from cStringIO import StringIO as MyIO
except:
    try:
        from StringIO import StringIO as MyIO
    except ImportError:
        from io import BytesIO as MyIO

# Python 2/3 switches
PYTHON_MAJOR_VERSION = sys.version_info[0]
if PYTHON_MAJOR_VERSION > 2:
    import urllib.parse as urlparse
    from past.builtins import basestring
else:
    import urlparse

# Python 3 compatibility shims
from . import six
from .six import binary_type
from .six import text_type
from .six import iteritems
from .six.moves import filter as ifilter
