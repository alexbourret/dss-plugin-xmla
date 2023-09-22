import copy
from xmla_constants import XMLAConstants


def extract_path(json_response, path_tokens):
    extract = copy.deepcopy(json_response)
    for path_token in path_tokens:
        extract = extract.pop(path_token, {})
        if extract is None:
            return []
    if not extract:
        return []
    elif type(extract) == dict:
        return [extract]
    else:
        return extract


def get_credentials(config):
    authentication_type = config.get("authentication_type", "None")
    credentials = config.get("{}_credentials".format(authentication_type), {})
    endpoint = credentials.get("endpoint")
    username = credentials.get("username")
    password = credentials.get("password")
    bearer_token = credentials.get("bearer_token")
    mdx_version = credentials.get("server_type", XMLAConstants.XMLA_DEFAULT_VERSION)
    return endpoint, mdx_version, username, password, bearer_token


class RecordsLimit():
    def __init__(self, records_limit=-1):
        self.has_no_limit = (records_limit == -1)
        self.records_limit = records_limit
        self.counter = 0

    def is_reached(self):
        if self.has_no_limit:
            return False
        self.counter += 1
        return self.counter > self.records_limit
