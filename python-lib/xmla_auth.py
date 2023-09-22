import requests
from safe_logger import SafeLogger


logger = SafeLogger("xmla plugin", forbidden_keys=["password", "bearer_token"])


class XMLAAuth(requests.auth.AuthBase):
    def __init__(self, version, username, password, bearer_token):
        self.version = version
        self.username = username
        self.password = password
        self.bearer_token = bearer_token
        if version == "basic":
            return (username, password)
        if version == "ntml":
            from requests_ntlm import HttpNtlmAuth
            return HttpNtlmAuth(username, password)
        if version == "kerberos":
            from requests_kerberos import HTTPKerberosAuth
            return HTTPKerberosAuth(principal=username, password=password)

    def __call__(self, request):
        request.headers["Authorization"] = "Bearer {}".format(self.bearer_token)
        return request
