"""Base mainnet attestation.

When the swarm reaches quorum, the finding stops being a private opinion: its
hash and the lenses that corroborated it are written to Base as a timestamped
first-discovery claim. The claim is a self-addressed 0-value transaction whose
calldata is the claim digest, so anyone can verify what was known and when
without the finding itself ever leaving the machine.

The signing key is read from the process environment at call time and is never
logged, printed or written to disk.
"""

from __future__ import annotations

import json
import os
from typing import Any

from web3 import Web3

CHAIN_ID = int(os.getenv("QUORUM_CHAIN_ID", "8453"))
EXPLORER = os.getenv("QUORUM_EXPLORER", "https://basescan.org/tx/")


def _w3() -> Web3:
    rpc = os.getenv("QUORUM_RPC") or os.getenv("BASE_RPC") or os.getenv("BASE_RPC_URL")
    if not rpc:
        raise RuntimeError("BASE_RPC is not set in the environment")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        raise RuntimeError("Base RPC did not respond")
    return w3


def _account(w3: Web3):
    key = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not key:
        raise RuntimeError("DEPLOYER_PRIVATE_KEY is not set in the environment")
    return w3.eth.account.from_key(key)


def claim_digest(finding: dict[str, Any]) -> bytes:
    """Deterministic digest of the published claim."""
    payload = json.dumps(
        {
            "risk": finding["risk"],
            "signature": finding["signature"],
            "contract": finding.get("contract"),
            "function": finding.get("function"),
            "corroborated_by": sorted(finding.get("seen_by", [])),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return Web3.keccak(text=payload)


def address() -> str:
    w3 = _w3()
    return _account(w3).address


def balance_wei() -> int:
    w3 = _w3()
    return w3.eth.get_balance(_account(w3).address)


def attest(finding: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """Publish one confirmed finding's digest to Base. Returns tx details."""
    w3 = _w3()
    acct = _account(w3)
    digest = claim_digest(finding)
    prefix = b"QUORUM1"  # so the calldata is self-describing on the explorer

    if dry_run:
        return {"dry_run": True, "from": acct.address, "digest": digest.hex(), "chain_id": CHAIN_ID}

    tx = {
        "from": acct.address,
        "to": acct.address,
        "value": 0,
        "data": prefix + digest,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": CHAIN_ID,
    }
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    fees = w3.eth.fee_history(1, "latest")
    base_fee = fees["baseFeePerGas"][-1]
    tx["maxPriorityFeePerGas"] = w3.to_wei(0.001, "gwei")
    tx["maxFeePerGas"] = base_fee * 2 + tx["maxPriorityFeePerGas"]

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return {
        "tx": tx_hash.hex(),
        "url": EXPLORER + tx_hash.hex(),
        "block": receipt["blockNumber"],
        "digest": digest.hex(),
        "gas_used": receipt["gasUsed"],
        "status": receipt["status"],
    }


PREFIX = b"QUORUM1"


def read_claim(tx_hash: str) -> dict[str, Any]:
    """Read a published claim back off Base."""
    w3 = _w3()
    tx = w3.eth.get_transaction(tx_hash)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    block = w3.eth.get_block(receipt["blockNumber"])
    data = bytes(tx["input"])
    if not data.startswith(PREFIX):
        raise RuntimeError("not a Quorum claim: calldata is missing the QUORUM1 prefix")
    return {
        "from": tx["from"],
        "digest": "0x" + data[len(PREFIX):].hex(),
        "block": receipt["blockNumber"],
        "timestamp": block["timestamp"],
        "status": receipt["status"],
    }
