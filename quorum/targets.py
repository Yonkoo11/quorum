"""Fetch real verified contract sources from five chains, with no API key.

Blockscout instances serve verified sources openly. Quorum only ever reads source that someone
already published on chain, and the only thing an explorer's answer can do here is be refused:
the file name is the contract's name with everything but [A-Za-z0-9_.-] replaced, the file goes
under targets/<chain>/, and a body over MAX_BYTES or without verified source is dropped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests

# The source explorers are not the claim chains in chain.py: a verify walks that table, and a
# fetch never needs a token or an RPC.
SOURCE_CHAINS = {
    "ethereum": ("https://eth.blockscout.com", 1),
    "base": ("https://base.blockscout.com", 8453),
    "arbitrum": ("https://arbitrum.blockscout.com", 42161),
    "optimism": ("https://optimism.blockscout.com", 10),
    "polygon": ("https://polygon.blockscout.com", 137),
}
DEFAULT_CHAIN = "base"
MAX_BYTES = 5 * 1024 * 1024
TARGET_DIR = Path(__file__).resolve().parent.parent / "targets"


def _chain(name: str) -> tuple[str, int]:
    try:
        return SOURCE_CHAINS[name]
    except KeyError:
        raise ValueError(f"unknown chain {name!r}; one of {', '.join(SOURCE_CHAINS)}") from None


def fetch_source(address: str, chain: str = DEFAULT_CHAIN, timeout: int = 30) -> tuple[str, str]:
    """Return (contract_name, source) for a verified address on one chain.

    A multi-file contract comes back as one file, each part preceded by a `// file: <path>` line
    so a line of evidence still says where it was read.
    """
    host, _ = _chain(chain)
    r = requests.get(f"{host}/api/v2/smart-contracts/{address}", timeout=timeout,
                     headers={"accept": "application/json"}, stream=True)
    if r.status_code == 404:
        raise RuntimeError(f"{address} has no verified source on {chain}")
    r.raise_for_status()
    body = r.raw.read(MAX_BYTES + 1, decode_content=True)
    if len(body) > MAX_BYTES:
        raise RuntimeError(f"{address} on {chain}: the explorer's answer is over {MAX_BYTES // (1024 * 1024)} MB; refused")
    try:
        payload = json.loads(body)
    except ValueError:
        raise RuntimeError(f"{address} on {chain}: the explorer did not answer with JSON") from None
    if not isinstance(payload, dict) or not payload.get("is_verified") or not payload.get("source_code"):
        raise RuntimeError(f"{address} has no verified source on {chain}")
    parts = [(payload.get("file_path") or f"{payload.get('name') or address}.sol", payload["source_code"])]
    for extra in payload.get("additional_sources") or []:
        if isinstance(extra, dict) and extra.get("source_code"):
            parts.append((extra.get("file_path") or "?", extra["source_code"]))
    src = "\n".join(f"// file: {path}\n{code}" for path, code in parts) if len(parts) > 1 else parts[0][1]
    name = str(payload.get("name") or address[:10])
    return name, src


def save(address: str, chain: str = DEFAULT_CHAIN) -> Path:
    _chain(chain)
    name, src = fetch_source(address, chain)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name).strip(".") or address[:10]
    folder = TARGET_DIR / chain
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{safe}.sol"
    path.write_text(src)
    return path


def load_targets(paths: list[str] | None = None) -> dict[str, str]:
    """Every target keyed by its path under targets/ (base/WETH9.sol), so one name on two chains stays two files."""
    if paths:
        files = [Path(p) for p in paths if Path(p).exists()]
        names = [f.name for f in files]
        # a bare name unless two given files share it (base/WETH9.sol and optimism/WETH9.sol): then the folder stays
        return {(f.name if names.count(f.name) == 1 else f"{f.parent.name}/{f.name}"): f.read_text() for f in files}
    files = sorted(TARGET_DIR.rglob("*.sol"))
    return {str(f.relative_to(TARGET_DIR)): f.read_text() for f in files if f.is_file()}
