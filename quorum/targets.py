"""Fetch real verified contract sources with no API key.

Blockscout instances serve verified sources openly, and cover five chains here. BNB Smart Chain
has no Blockscout instance and BscScan wants a key, so that one chain is read from Sourcify, whose
v2 API is equally keyless. Which backend a chain uses is the only difference; both return the same
(name, source) pair and are refused on the same terms.

Quorum only ever reads source that someone already published on chain, and the only thing an
explorer's answer can do here is be refused: the file name is the contract's name with everything
but [A-Za-z0-9_.-] replaced, the file goes under targets/<chain>/, and a body over MAX_BYTES or
without verified source is dropped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests

# The source explorers are not the claim chains in chain.py: a verify walks that table, and a
# fetch never needs a token or an RPC.
SOURCIFY = "https://sourcify.dev/server"
SOURCE_CHAINS = {
    "ethereum": ("https://eth.blockscout.com", 1),
    "base": ("https://base.blockscout.com", 8453),
    "arbitrum": ("https://arbitrum.blockscout.com", 42161),
    "optimism": ("https://optimism.blockscout.com", 10),
    "polygon": ("https://polygon.blockscout.com", 137),
    # No Blockscout instance for BNB Smart Chain, so this one goes to Sourcify.
    "bsc": (None, 56),
}
DEFAULT_CHAIN = "base"
MAX_BYTES = 5 * 1024 * 1024
TARGET_DIR = Path(__file__).resolve().parent.parent / "targets"


def _chain(name: str) -> tuple[str, int]:
    try:
        return SOURCE_CHAINS[name]
    except KeyError:
        raise ValueError(f"unknown chain {name!r}; one of {', '.join(SOURCE_CHAINS)}") from None


def _ask(url: str, address: str, chain: str, timeout: int) -> dict:
    """One explorer call, refused rather than trusted: 404 means unverified, and an answer over
    MAX_BYTES or that is not JSON is dropped without being parsed into the corpus."""
    r = requests.get(url, timeout=timeout, headers={"accept": "application/json"}, stream=True)
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
    if not isinstance(payload, dict):
        raise RuntimeError(f"{address} on {chain}: the explorer did not answer with JSON")
    return payload


def _join(parts: list[tuple[str, str]]) -> str:
    """One file per contract. A multi-file contract keeps a `// file: <path>` line before each
    part, so a line of evidence still says where it was read."""
    if len(parts) == 1:
        return parts[0][1]
    return "\n".join(f"// file: {path}\n{code}" for path, code in parts)


def _from_blockscout(address: str, chain: str, host: str, timeout: int) -> tuple[str, str]:
    payload = _ask(f"{host}/api/v2/smart-contracts/{address}", address, chain, timeout)
    if not payload.get("is_verified") or not payload.get("source_code"):
        raise RuntimeError(f"{address} has no verified source on {chain}")
    parts = [(payload.get("file_path") or f"{payload.get('name') or address}.sol", payload["source_code"])]
    for extra in payload.get("additional_sources") or []:
        if isinstance(extra, dict) and extra.get("source_code"):
            parts.append((extra.get("file_path") or "?", extra["source_code"]))
    return str(payload.get("name") or address[:10]), _join(parts)


def _from_sourcify(address: str, chain: str, chain_id: int, timeout: int) -> tuple[str, str]:
    payload = _ask(f"{SOURCIFY}/v2/contract/{chain_id}/{address}?fields=sources,compilation",
                   address, chain, timeout)
    sources = payload.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise RuntimeError(f"{address} has no verified source on {chain}")
    parts = [(path, body["content"]) for path, body in sorted(sources.items())
             if isinstance(body, dict) and body.get("content")]
    if not parts:
        raise RuntimeError(f"{address} has no verified source on {chain}")
    name = str((payload.get("compilation") or {}).get("name") or address[:10])
    return name, _join(parts)


def fetch_source(address: str, chain: str = DEFAULT_CHAIN, timeout: int = 30) -> tuple[str, str]:
    """Return (contract_name, source) for a verified address on one chain."""
    host, chain_id = _chain(chain)
    if host is None:
        return _from_sourcify(address, chain, chain_id, timeout)
    return _from_blockscout(address, chain, host, timeout)


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
