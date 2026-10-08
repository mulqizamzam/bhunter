import fnmatch
from urllib.parse import urlparse


class Scope:
    def __init__(self, cfg):
        self.in_scope = cfg["scope"]["in_scope"]
        self.out_of_scope = cfg["scope"].get("out_of_scope", [])
        self.max_rps = cfg["scope"].get("max_rps", 10)

    def _match(self, host, patterns):
        return any(fnmatch.fnmatch(host, p) for p in patterns)

    def allows(self, url):
        host = urlparse(url).hostname or ""
        if self._match(host, self.out_of_scope):
            return False
        return self._match(host, self.in_scope)
