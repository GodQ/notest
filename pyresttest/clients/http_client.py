# import pycurl
# from pyresttest.import_base import *


DEFAULT_TIMEOUT = 10  # Seconds
HTTP_CLIENT = "pycurl"

if HTTP_CLIENT == "pycurl":
    from pyresttest.clients.pycurl_client import PyCurlClient as HttpClient
else:
    from pyresttest.clients.requests_client import RequestsClient as HttpClient



