from pyresttest.import_base import *
import requests


class RequestsClient:

    @staticmethod
    def get_new_handler():
        return requests

    @staticmethod
    def configure(test_obj, timeout=DEFAULT_TIMEOUT, context=None,
                       curl_handle=None, ssl_insecure=True):
        """ Create and mostly configure a curl object for test, reusing existing if possible """

        if curl_handle:
            curl = curl_handle

            try:  # Check the curl handle isn't closed, and reuse it if possible
                curl.getinfo(curl.HTTP_CODE)
                # Below clears the cookies & curl options for clean run
                # But retains the DNS cache and connection pool
                curl.reset()
                curl.setopt(curl.COOKIELIST, "ALL")
            except pycurl.error:
                curl = pycurl.Curl()

        else:
            curl = pycurl.Curl()

        return curl