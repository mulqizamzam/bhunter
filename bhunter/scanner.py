import httpx


class Scanner:
    def __init__(self, cfg, scope):
        self.cfg = cfg
        self.scope = scope
        self.client = httpx.Client(
            timeout=cfg["scan"]["timeout"],
            headers={"User-Agent": cfg["scan"]["user_agent"],
                     **cfg["scan"].get("headers", {})},
            follow_redirects=cfg["scan"]["follow_redirects"],
        )

    def probe(self, url):
        if not self.scope.allows(url):
            return None
        try:
            r = self.client.get(url)
            return {
                "url": url,
                "status": r.status_code,
                "length": len(r.content),
                "server": r.headers.get("server"),
                "content_type": r.headers.get("content-type"),
            }
        except httpx.HTTPError as e:
            return {"url": url, "error": str(e)}
