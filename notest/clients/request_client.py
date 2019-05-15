

# DEFAULT_TIMEOUT = 10  # Seconds
# HTTP_CLIENT = "requests"    # requests or pycurl
#
# if HTTP_CLIENT == "pycurl":
#     try:
#         import pycurl
#     except:
#         print("pycurl is not installed successfully, change to requests")
#         HTTP_CLIENT = "requests"
#
# if HTTP_CLIENT == "pycurl":
#     from notest.clients.pycurl_client import PyCurlClient as HttpClient
# elif HTTP_CLIENT == "requests":
#     from notest.clients.requests_client import RequestsClient as HttpClient
# else:
#     raise Exception("Unknown Http Client Type: {}".format(HTTP_CLIENT))


def get_client_class(client_type="requests"):
    if client_type == "pycurl":
        from notest.clients.pycurl_client import PyCurlClient as HttpClient
        return HttpClient
    elif client_type == "requests":
        from notest.clients.requests_client import RequestsClient as HttpClient
        return HttpClient
    else:
        raise Exception("Unknown Client Type: {}".format(client_type))
