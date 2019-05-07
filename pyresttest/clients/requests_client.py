# from pyresttest.import_base import *
import requests
import json
import os

from pyresttest.import_base import *
from .http_auth_type import HttpAuthType
from .http_response import HttpResponse

base_dir = os.path.abspath(os.path.dirname(__file__))

DEFAULT_TIMEOUT = 10  # Seconds


class RequestsClient:
    def __init__(self, handler=None):
        if not handler or not isinstance(handler, requests.Session):
            self.session = requests.Session()
        else:
            self.session = handler
        self.response = None
        self.Http_Method_Map = {
            "post": self.session.post,
            "get": self.session.get,
            "put": self.session.put,
            "delete": self.session.delete,
            "multipart_post": self.session.post,
        }

    def get_handler(self):
        return self.session

    @staticmethod
    def close_handler(handler):
        if handler:
            handler.close()

    def close(self):
        if self.session:
            self.session.close()

    def send_request(self, test_obj, timeout=DEFAULT_TIMEOUT,
                     context=None,
                     handler=None, ssl_insecure=True, verbose=False):

        if handler:
            session = handler
        else:
            session = self.session

        # https://2.python-requests.org//zh_CN/latest/user/advanced.html
        request_obj = requests.Request(
            method=test_obj.method,
            url=str(test_obj.url),
        )
        request_obj = session.prepare_request(request_obj)

        if test_obj.auth_username and test_obj.auth_password:
            request_obj.auth = {test_obj.auth_username, test_obj.auth_password}

            if test_obj.auth_type:
                pass

        head = test_obj.get_headers(context=context)
        headers = {k.lower(): v for k, v in head.items()}
        # Set charset if doing unicode conversion and not set explicitly
        body = test_obj.http_body
        body_type = "data"
        if isinstance(body, str):  # Encode unicode
            # body = body.encode('UTF-8')
            if 'content-type' in headers.keys():
                content = headers['content-type']
                if 'json' in content:
                    body = json.loads(body)
                    body_type = "json"
                if 'charset' not in content:
                    headers['content-type'] = content + ' ; charset=UTF-8'

        if body_type == "json":
            request_obj.prepare_body(data=None, files=None, json=body)
        elif body_type == "data":
            request_obj.prepare_body(data=body, files=None, json=None)

        request_obj.headers.update(headers)


        verify = False
        if ssl_insecure is True:
            verify = False
        cert = None
        if "cert" in test_obj.__dict__ and test_obj.cert:
            cert = test_obj.cert
        proxies = None
        if "proxies" in test_obj.__dict__ and test_obj.proxies:
            proxies = test_obj.proxies

        if verbose:
            pass

        resp = session.send(
            request=request_obj,
            verify=verify,
            timeout=timeout,
            cert=cert,
            proxies=proxies
        )

        response = HttpResponse(
            requests_response=resp
        )
        self.response = response

        return response
