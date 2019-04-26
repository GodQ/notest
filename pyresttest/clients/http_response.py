
class HttpResponse:
    def __init__(self, body, headers, status_code, reason=None):
        self.body = body
        self.headers = headers
        self.status_code = status_code
        self.reason = reason