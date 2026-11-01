"""Upstream drift: the facts Quorum's Zcash checks rest on, re-fetched from their sources.

Same ```facts block format and host allow-list as zcash-skills docs/check-facts.py (read
2026-11-01), so a block can be moved between the two files unchanged. A fact drifts when the
value extracted from `upstream` no longer matches `value`; a fetch or extract failure is UNKNOWN,
never "no drift". A new Zebra release or advisory is the signal to re-read the Zcash rules.

Usage: python3 -m watch.drift [--facts watch/zcash-facts.md] [--log ai/drift.jsonl] [--notify]
Exit 0 = every fact agrees, 1 = drift, 2 = at least one unknown.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .simulate import redact

ORACLE_HOSTS = {"raw.githubusercontent.com", "github.com", "zips.z.cash", "zcash.readthedocs.io", "z.cash"}
FETCH_MAX_BYTES = 2_000_000
FACTS = Path(__file__).with_name("zcash-facts.md")


def host_allowed(url: str) -> bool:
    u = urllib.parse.urlsplit(url)
    return u.scheme == "https" and u.hostname in ORACLE_HOSTS


class _AllowlistRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not host_allowed(newurl):
            raise ValueError(f"redirect off the allow-list: {redact(newurl)}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_AllowlistRedirects)


def fetch(url: str, timeout: int = 30) -> str:
    if not host_allowed(url):
        raise ValueError(f"host not allowed: {redact(url)}")
    req = urllib.request.Request(url, headers={"User-Agent": "quorum-watch-drift"})
    with _opener.open(req, timeout=timeout) as resp:
        return resp.read(FETCH_MAX_BYTES).decode("utf-8", "replace")


def parse_facts(text: str) -> list[dict]:
    facts = []
    for block in re.findall(r"```facts\n(.*?)```", text, re.S):
        f = dict(re.findall(r"^(\w+):\s*(.+)$", block, re.M))
        if "id" in f:
            facts.append(f)
    return facts


def upstream_value(fact: dict, fetch=fetch) -> str:
    if not host_allowed(fact["upstream"]):       # checked here too, whatever fetcher is passed in
        raise ValueError(f"host not allowed: {redact(fact['upstream'])}")
    text = fetch(fact["upstream"])
    matches = [m.group(1) for m in re.finditer(fact["extract"], text, re.M)]
    if not matches or not all(matches):
        raise ValueError("extract pattern matched nothing")
    if fact.get("extract_all") == "true":
        return ", ".join(sorted(set(matches)))
    return matches[0]


def norm(text: str) -> str:
    return re.sub(r"[`,\s]", "", text).lower()


def check(facts: list[dict], fetch=fetch) -> list[dict]:
    out = []
    for f in facts:
        row = {"id": f["id"], "value": f["value"], "upstream": f["upstream"], "wall": time.time()}
        try:
            row["current"] = upstream_value(f, fetch)
            row["drift"] = norm(row["current"]) != norm(f["value"])
        except Exception as exc:       # network, off-list redirect, bad extract: all unknown
            row["unknown"] = redact(exc)
        out.append(row)
    return out


def report(rows: list[dict]) -> tuple[int, list[str]]:
    lines, code = [], 0
    for r in rows:
        if "unknown" in r:
            lines.append(f"[Quorum drift] UNKNOWN {r['id']}: {r['unknown']}"); code = max(code, 2)
        elif r["drift"]:
            lines.append(f"[Quorum drift] {r['id']} changed: was {r['value']}, now {r['current']}"); code = max(code, 1)
        else:
            lines.append(f"ok {r['id']} = {r['value']}")
    return code, lines


def main(argv=None):
    from .live import make_notifier
    p = argparse.ArgumentParser()
    p.add_argument("--facts", default=str(FACTS))
    p.add_argument("--log", default="ai/drift.jsonl")
    p.add_argument("--notify", action="store_true", help="send drift and unknown lines to Telegram")
    a = p.parse_args(argv)
    rows = check(parse_facts(Path(a.facts).read_text()))
    Path(a.log).parent.mkdir(parents=True, exist_ok=True)
    with open(a.log, "a") as log:
        log.write(json.dumps(rows) + "\n")
    code, lines = report(rows)
    notify = make_notifier(not a.notify)
    for line in lines:
        notify(line) if line.startswith("[Quorum drift]") else print(line)
    if hasattr(notify, "flush"):
        notify.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
