import yaml
import httpx
from concurrent.futures import ThreadPoolExecutor


def load_rules(path):
    with open(path) as f:
        return yaml.safe_load(f)


class Fuzzer:
    def __init__(self, cfg, scope):
        self.cfg = cfg
        self.scope = scope
        self.concurrency = cfg["fuzz"]["concurrency"]

    def _inject(self, url, param, payload):
        from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
        u = urlparse(url)
        q = parse_qs(u.query)
        q[param] = [payload]
        return urlunparse(u._replace(query=urlencode(q, doseq=True)))

    def run(self, url, param, payloads):
        results = []

        def one(p):
            target = self._inject(url, param, p)
            if not self.scope.allows(target):
                return None
            try:
                r = httpx.get(target, timeout=self.cfg["scan"]["timeout"])
                return {"payload": p, "status": r.status_code,
                        "len": len(r.content), "body_snip": r.text[:200]}
            except httpx.HTTPError:
                return None

        with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            for res in ex.map(one, payloads):
                if res:
                    results.append(res)
        return results
