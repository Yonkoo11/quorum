"""Minimal JSON-RPC reader for the watch stage.

Rules: every call returns a value or None. None means "unknown", never "clean".
Callers must log unknowns; they must not treat them as a pass.
"""
from __future__ import annotations

import json
import re
import os
import time
import urllib.error
import urllib.request

UA = "quorum-watch/0.1"

CHAIN_ENV = {
    "ethereum": "ETHEREUM_RPC_URL",
    "arbitrum": "ARBITRUM_RPC_URL",
    "base": "BASE_RPC_URL",
}
# Public fallbacks (verified answering 2026-11-01 with a User-Agent header).
PUBLIC_RPC = {
    "ethereum": "https://eth.drpc.org",
    "arbitrum": "https://arbitrum.drpc.org",
}


def rpc_url(chain: str) -> str:
    env = CHAIN_ENV.get(chain)
    url = os.getenv(env, "") if env else ""
    return url or PUBLIC_RPC[chain]


def redact(text, secret: str | None = None) -> str:
    """Strip URLs of any scheme (an RPC URL can carry an API key) before an error reaches an alert
    or a log; `secret` (the configured endpoint, or any token) is removed wherever it appears, URL or not."""
    text = str(text)
    if secret and len(secret) > 8:
        text = text.replace(secret, "<endpoint>")
    return re.sub(r"\w+://\S+", "<url>", text)


class Rpc:
    def __init__(self, chain: str, url: str | None = None, retries: int = 2):
        self.chain = chain
        self.url = url or rpc_url(chain)
        self.retries = retries
        self.calls = 0
        self.failures = 0
        self.last_error = None      # the RPC's own error text for the most recent failed call

    def call(self, method: str, params: list):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(self.url, data=body, headers={
            "content-type": "application/json", "user-agent": UA})
        for attempt in range(self.retries + 1):
            self.calls += 1
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    out = json.loads(r.read())
                if "result" in out:
                    return out["result"]
                self.last_error = f"{method}: {out.get('error')}"
                break  # an RPC-level error will not fix itself on retry
            except urllib.error.HTTPError as exc:
                self.last_error = f"{method}: {exc}"
                if 400 <= exc.code < 500 and exc.code != 429:
                    break  # the endpoint refused the request (e.g. a span limit); retrying cannot help
                time.sleep(1.5 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                self.last_error = f"{method}: {exc}"
                time.sleep(1.5 * (attempt + 1))
        self.failures += 1
        return None

    def block(self, number: int) -> dict | None:
        return self.call("eth_getBlockByNumber", [hex(number), True])

    def header(self, number: int) -> dict | None:
        """Block without transaction bodies (range mode on fast chains reads only this)."""
        return self.call("eth_getBlockByNumber", [hex(number), False])

    def head(self) -> int | None:
        h = self.call("eth_blockNumber", [])
        return int(h, 16) if h else None

    def code(self, address: str, block: int | str = "latest") -> str | None:
        tag = hex(block) if isinstance(block, int) else block
        return self.call("eth_getCode", [address, tag])

    def logs(self, addresses: list[str], from_block: int, to_block: int) -> list | None:
        if not addresses:
            return []
        return self.call("eth_getLogs", [{
            "address": addresses, "fromBlock": hex(from_block), "toBlock": hex(to_block)}])
