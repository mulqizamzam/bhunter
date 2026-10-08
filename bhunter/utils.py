import time


class RateLimiter:
    def __init__(self, rps):
        self.interval = 1.0 / rps
        self.last = 0.0

    def wait(self):
        now = time.monotonic()
        delta = now - self.last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self.last = time.monotonic()
