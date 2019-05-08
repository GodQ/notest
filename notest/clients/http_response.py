
class HttpResponse:
    def __init__(self, body=None, headers=None, status_code=None,
                 reason=None, cookies=None, requests_response=None):
        if requests_response is not None:
            self.body = requests_response.content
            requests_headers = requests_response.headers
            self.headers = [i for i in requests_headers.lower_items()]
            # self.headers = {k: v for k, v in requests_headers.lower_items()}
            self.status_code = requests_response.status_code
            self.reason = requests_response.reason
            self.cookies = requests_response.cookies
        else:
            self.body = body
            self.headers = headers
            self.status_code = status_code
            self.reason = reason
            self.cookies = cookies