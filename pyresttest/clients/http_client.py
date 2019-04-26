# import pycurl
# from pyresttest.import_base import *


DEFAULT_TIMEOUT = 10  # Seconds
HTTP_CLIENT = "requests"

if HTTP_CLIENT == "pycurl":
    from pyresttest.clients.pycurl_client import PyCurlClient as HttpClient
elif HTTP_CLIENT == "requests":
    from pyresttest.clients.requests_client import RequestsClient as HttpClient
else:
    raise Exception("Unknown Http Client Type: {}".format(HTTP_CLIENT))



