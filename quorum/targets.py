"""Fetch real verified contract sources from Base mainnet.

No API key: Blockscout serves verified sources for Base openly. Quorum only
ever reads source that someone already published on chain.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests

BLOCKSCOUT = "https://base.blockscout.com/api"
TARGET_DIR = Path(__file__).resolve().parent.parent / "targets"


def fetch_source(address: str, timeout: int = 30) -> tuple[str, str]:
    """Return (contract_name, flattened_source) for a verified Base address."""
    r = requests.get(
        BLOCKSCOUT,
        params={"module": "contract", "action": "getsourcecode", "address": address},
        timeout=timeout,
        headers={"accept": "application/json"},
    )
    r.raise_for_status()
    payload = r.json()
    result = (payload.get("result") or [{}])[0]
    src = result.get("SourceCode") or ""
    name = result.get("ContractName") or address[:10]
    if not src:
        raise RuntimeError(f"{address} has no verified source on Base")

    # Standard-json bundles arrive wrapped in an extra pair of braces.
    if src.strip().startswith("{"):
        blob = src.strip()
        if blob.startswith("{{"):
            blob = blob[1:-1]
        try:
            parsed = json.loads(blob)
            sources = parsed.get("sources", parsed)
            src = "\n".join(v.get("content", "") for v in sources.values() if isinstance(v, dict))
        except json.JSONDecodeError:
            pass
    return name, src


def save(address: str) -> Path:
    name, src = fetch_source(address)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    TARGET_DIR.mkdir(exist_ok=True)
    path = TARGET_DIR / f"{safe}.sol"
    path.write_text(src)
    return path


def load_targets(paths: list[str] | None = None) -> dict[str, str]:
    files = [Path(p) for p in paths] if paths else sorted(TARGET_DIR.glob("*.sol"))
    return {f.name: f.read_text() for f in files if f.exists()}
