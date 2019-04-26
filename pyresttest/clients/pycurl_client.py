import pycurl
from pyresttest.import_base import *
from .http_auth_type import HttpAuthType
from .http_response import HttpResponse


base_dir = os.path.abspath(os.path.dirname(__file__))
libcurl_dir = os.path.join(base_dir, "..", "..", "tools", "libcurl_win64")

if sys.platform.find("win") > -1:
    sys.path.append(libcurl_dir)


DEFAULT_TIMEOUT = 10  # Seconds
# Map HTTP method names to curl methods
# Kind of obnoxious that it works this way...
HTTP_METHODS = {u'GET': pycurl.HTTPGET,
                u'PUT': pycurl.UPLOAD,
                u'PATCH': pycurl.POSTFIELDS,
                u'POST': pycurl.POST,
                u'DELETE': 'DELETE'}


HttpAuthType_Map = {
    HttpAuthType.HTTP_AUTH_BASIC: pycurl.HTTPAUTH_BASIC
}


class PyCurlClient:
    def __init__(self, handler=None):
        if not handler or not isinstance(handler, pycurl.Curl):
            self.handler = pycurl.Curl()
        else:
            self.handler = handler
        self.response = None

    def get_handler(self):
        return self.handler

    @staticmethod
    def close_handler(handler):
        if handler:
            handler.close()

    def close(self):
        if self.handler:
            self.handler.close()

    def send_request(self, test_obj, timeout=DEFAULT_TIMEOUT, context=None,
                     handler=None, ssl_insecure=True, verbose=False):
        """ Create and mostly configure a curl object for test, reusing existing if possible """

        if handler:
            curl = handler

            try:  # Check the curl handle isn't closed, and reuse it if possible
                curl.getinfo(curl.HTTP_CODE)
                # Below clears the cookies & curl options for clean run
                # But retains the DNS cache and connection pool
                curl.reset()
                curl.setopt(curl.COOKIELIST, "ALL")
            except pycurl.error:
                curl = pycurl.Curl()

        else:
            curl = self.handler

        # curl.setopt(pycurl.VERBOSE, 1)  # Debugging convenience
        curl.setopt(curl.URL, str(test_obj.url))
        curl.setopt(curl.TIMEOUT, timeout)

        is_unicoded = False
        bod = test_obj.body
        if isinstance(bod, text_type):  # Encode unicode
            bod = bod.encode('UTF-8')
            is_unicoded = True

        # Set read function for post/put bodies
        if bod and len(bod) > 0:
            curl.setopt(curl.READFUNCTION, MyIO(bod).read)

        if test_obj.auth_username and test_obj.auth_password:
            curl.setopt(pycurl.USERPWD,
                        parsing.encode_unicode_bytes(
                            test_obj.auth_username) + b':' +
                        parsing.encode_unicode_bytes(test_obj.auth_password))
            if test_obj.auth_type:
                auth_type = HttpAuthType_Map[test_obj.auth_type]
                curl.setopt(pycurl.HTTPAUTH, auth_type)

        if test_obj.method == u'POST':
            curl.setopt(HTTP_METHODS[u'POST'], 1)
            # Required for some servers
            if bod is not None:
                curl.setopt(pycurl.POSTFIELDSIZE, len(bod))
            else:
                curl.setopt(pycurl.POSTFIELDSIZE, 0)
        elif test_obj.method == u'PUT':
            curl.setopt(HTTP_METHODS[u'PUT'], 1)
            # Required for some servers
            if bod is not None:
                curl.setopt(pycurl.INFILESIZE, len(bod))
            else:
                curl.setopt(pycurl.INFILESIZE, 0)
        elif test_obj.method == u'PATCH':
            curl.setopt(curl.POSTFIELDS, bod)
            curl.setopt(curl.CUSTOMREQUEST, 'PATCH')
            # Required for some servers
            # I wonder: how compatible will this be?  It worked with Django but feels iffy.
            if bod is not None:
                curl.setopt(pycurl.INFILESIZE, len(bod))
            else:
                curl.setopt(pycurl.INFILESIZE, 0)
        elif test_obj.method == u'DELETE':
            curl.setopt(curl.CUSTOMREQUEST, 'DELETE')
            if bod is not None:
                curl.setopt(pycurl.POSTFIELDS, bod)
                curl.setopt(pycurl.POSTFIELDSIZE, len(bod))
        elif test_obj.method == u'HEAD':
            curl.setopt(curl.NOBODY, 1)
            curl.setopt(curl.CUSTOMREQUEST, 'HEAD')
        elif test_obj.method and test_obj.method.upper() != 'GET':  # Alternate HTTP methods
            curl.setopt(curl.CUSTOMREQUEST, test_obj.method.upper())
            if bod is not None:
                curl.setopt(pycurl.POSTFIELDS, bod)
                curl.setopt(pycurl.POSTFIELDSIZE, len(bod))

        # Template headers as needed and convert headers dictionary to list of header entries
        head = test_obj.get_headers(context=context)
        head = copy.copy(head)  # We're going to mutate it, need to copy

        # Set charset if doing unicode conversion and not set explicitly
        # TESTME
        if is_unicoded and u'content-type' in head.keys():
            content = head[u'content-type']
            if u'charset' not in content:
                head[u'content-type'] = content + u' ; charset=UTF-8'

        if head:
            headers = [str(headername) + ':' + str(headervalue)
                       for headername, headervalue in head.items()]
        else:
            headers = list()
        # Fix for expecting 100-continue from server, which not all servers
        # will send!
        headers.append("Expect:")
        headers.append("Connection: close")
        curl.setopt(curl.HTTPHEADER, headers)

        # Set custom curl options, which are KEY:VALUE pairs matching the pycurl option names
        # And the key/value pairs are set
        if test_obj.curl_options:
            filterfunc = lambda x: x[0] is not None and x[
                1] is not None  # Must have key and value
            for (key, value) in ifilter(filterfunc,
                                        test_obj.curl_options.items()):
                # getattr to look up constant for variable name
                curl.setopt(getattr(curl, key), value)

        # reset the body, it holds values from previous runs otherwise
        headers = MyIO()
        body = MyIO()
        if sys.platform.find("win") > -1:
            curl.setopt(pycurl.CAINFO,
                        os.path.join(libcurl_dir,
                                     "curl-ca-bundle.crt"))
        curl.setopt(pycurl.WRITEFUNCTION, body.write)
        curl.setopt(pycurl.HEADERFUNCTION, headers.write)
        if verbose:
            curl.setopt(pycurl.VERBOSE, True)
        if ssl_insecure is True:
            curl.setopt(pycurl.SSL_VERIFYPEER, 0)
            curl.setopt(pycurl.SSL_VERIFYHOST, 0)

        curl.perform()  # Run the actual call

        response_body = body.getvalue()
        body.close()
        response_headers = headers.getvalue()
        headers.close()
        response_code = curl.getinfo(pycurl.RESPONSE_CODE)
        response = HttpResponse(
            body=response_body,
            headers=response_headers,
            status_code=response_code
        )
        self.response = response

        return response

