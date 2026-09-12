"""Claims on Robinhood Chain.

When the swarm reaches quorum, the finding stops being a private opinion: its
hash and the lenses that corroborated it are written to Robinhood Chain as a
timestamped first-discovery claim. The claim is a self-addressed 0-value transaction whose
calldata is the claim digest, so anyone can verify what was known and when
without the finding itself ever leaving the machine.

Publishing a claim costs a fixed amount of QUORUM, burned through the token
contract's own burn(uint256) on the same chain before the claim is written.
The claim carries the burn's transaction hash, so a verifier can check both
halves: that the digest was published, and that the fee was really destroyed.
The fee exists for one reason: a public registry of known bug patterns needs a
cost to publish or it fills with junk. Nobody receives the fee. Scanning,
memory and recall never touch the token; only publishing does.

The token, and so the fee, lives on Robinhood Chain. Claims default to the same
chain so a verifier needs one RPC, not two. The first claim (Base, block
51138878) predates both the fee and the move; read_claim still finds it there,
and QUORUM_CHAIN_ID can point new claims at any chain in CHAINS.

The signing key is read from the process environment at call time and is never
logged, printed or written to disk.
"""

from __future__ import annotations

import json
import os
from typing import Any

from web3 import Web3
from web3.exceptions import TransactionNotFound

# Every chain a claim may live on. RPC comes from the first env var that is set,
# else the public endpoint. The token is only ever on TOKEN_CHAIN_ID.
CHAINS = {
    4663: {"name": "Robinhood Chain", "rpc_env": ("QUORUM_RPC", "QUORUM_TOKEN_RPC"),
           "rpc": "https://rpc.mainnet.chain.robinhood.com",
           "explorer": "https://robinhoodchain.blockscout.com/tx/"},
    8453: {"name": "Base", "rpc_env": ("BASE_RPC", "BASE_RPC_URL"),
           "rpc": "https://mainnet.base.org",
           "explorer": "https://basescan.org/tx/"},
}
TOKEN_CHAIN_ID = 4663
CHAIN_ID = int(os.getenv("QUORUM_CHAIN_ID", str(TOKEN_CHAIN_ID)))
if CHAIN_ID not in CHAINS:
    raise RuntimeError(f"QUORUM_CHAIN_ID={CHAIN_ID} is not a chain Quorum claims on: {sorted(CHAINS)}")
PREFIX = b"QUORUM1"  # v1 claim: digest only (the first claim, Base block 51138878, is this shape)
PREFIX_V2 = b"QUORUM2"  # v2 claim: digest + fee burn tx hash
EXPLORER = os.getenv("QUORUM_EXPLORER", CHAINS[CHAIN_ID]["explorer"])

TOKEN = Web3.to_checksum_address("0xa6452Fd7134218f62056a304eaf501F8714A26b9")
TOKEN_DECIMALS = 18
CLAIM_FEE = 1_000 * 10**TOKEN_DECIMALS  # 1,000 QUORUM per published claim, burned
TOKEN_EXPLORER = os.getenv("QUORUM_TOKEN_EXPLORER", CHAINS[TOKEN_CHAIN_ID]["explorer"])
BURN_SELECTOR = Web3.keccak(text="burn(uint256)")[:4]
_TOKEN_ABI = [
    {"name": "burn", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "amount", "type": "uint256"}], "outputs": []},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "a", "type": "address"}], "outputs": [{"type": "uint256"}]},
]


def chain_name(chain_id: int | None = None) -> str:
    return CHAINS[chain_id or CHAIN_ID]["name"]


def _rpc(chain_id: int) -> str:
    spec = CHAINS[chain_id]
    return next((os.environ[e] for e in spec["rpc_env"] if os.getenv(e)), spec["rpc"])


def _w3(chain_id: int | None = None) -> Web3:
    """A connection to the claim chain (default) or any chain in CHAINS, checked by id."""
    chain_id = chain_id or CHAIN_ID
    w3 = Web3(Web3.HTTPProvider(_rpc(chain_id), request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        raise RuntimeError(f"{chain_name(chain_id)} RPC did not respond")
    if w3.eth.chain_id != chain_id:
        raise RuntimeError(f"RPC for {chain_name(chain_id)} answered as chain {w3.eth.chain_id}, expected {chain_id}")
    return w3


def _token_w3() -> Web3:
    return _w3(TOKEN_CHAIN_ID)


def _find_tx(tx_hash: str) -> tuple[int, Web3, Any]:
    """Locate a claim or reveal: the claim chain first, then every other chain a claim has lived on.

    Only "not on this chain" moves on to the next one. An RPC that is down raises,
    so a verifier is never told a claim is missing when the truth is the node was.
    """
    for cid in [CHAIN_ID, *(c for c in CHAINS if c != CHAIN_ID)]:
        w3 = _w3(cid)
        try:
            return cid, w3, w3.eth.get_transaction(tx_hash)
        except TransactionNotFound:
            continue
    raise RuntimeError(f"{tx_hash} is not on any chain Quorum claims on ({', '.join(chain_name(c) for c in CHAINS)})")


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
    """Gas held by the signer on the claim chain."""
    w3 = _w3()
    return w3.eth.get_balance(_account(w3).address)


def token_balance() -> int:
    """QUORUM held by the signer on Robinhood Chain, in base units."""
    w3 = _token_w3()
    token = w3.eth.contract(address=TOKEN, abi=_TOKEN_ABI)
    return token.functions.balanceOf(_account(w3).address).call()


def _send(w3: Web3, acct, tx: dict[str, Any]) -> dict[str, Any]:
    tx["nonce"] = w3.eth.get_transaction_count(acct.address)
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    fees = w3.eth.fee_history(1, "latest")
    tx["maxPriorityFeePerGas"] = w3.to_wei(0.001, "gwei")
    tx["maxFeePerGas"] = fees["baseFeePerGas"][-1] * 2 + tx["maxPriorityFeePerGas"]
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return {"tx": tx_hash.hex(), "block": receipt["blockNumber"], "gas_used": receipt["gasUsed"],
            "status": receipt["status"]}


def burn_fee() -> dict[str, Any]:
    """Burn CLAIM_FEE QUORUM through the token's own burn(). Raises if it fails."""
    w3 = _token_w3()
    acct = _account(w3)
    token = w3.eth.contract(address=TOKEN, abi=_TOKEN_ABI)
    held = token.functions.balanceOf(acct.address).call()
    if held < CLAIM_FEE:
        raise RuntimeError(
            f"publishing a claim burns {CLAIM_FEE // 10**TOKEN_DECIMALS:,} QUORUM; "
            f"signer holds {held / 10**TOKEN_DECIMALS:,.0f} on Robinhood Chain"
        )
    tx = token.functions.burn(CLAIM_FEE).build_transaction({"from": acct.address, "chainId": TOKEN_CHAIN_ID})
    result = _send(w3, acct, tx)
    if result["status"] != 1:
        raise RuntimeError(f"fee burn reverted: {result['tx']}")
    result["url"] = TOKEN_EXPLORER + result["tx"]
    result["amount"] = CLAIM_FEE
    return result


def read_burn(tx_hash: str) -> dict[str, Any]:
    """Read a fee burn back off Robinhood Chain and check it is what a claim requires."""
    w3 = _token_w3()
    tx = w3.eth.get_transaction(tx_hash)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    data = bytes(tx["input"])
    ok_call = tx["to"] == TOKEN and data[:4] == BURN_SELECTOR and len(data) == 36
    amount = int.from_bytes(data[4:36], "big") if ok_call else 0
    return {
        "from": tx["from"],
        "amount": amount,
        "block": receipt["blockNumber"],
        "status": receipt["status"],
        "valid": bool(ok_call and receipt["status"] == 1 and amount >= CLAIM_FEE),
    }


def encode_claim(digest: bytes, burn_tx: bytes) -> bytes:
    """v2 calldata: QUORUM2 | digest (32) | burn tx hash (32)."""
    if len(digest) != 32 or len(burn_tx) != 32:
        raise ValueError("digest and burn tx hash must both be 32 bytes")
    return PREFIX_V2 + digest + burn_tx


def decode_claim(data: bytes) -> dict[str, Any]:
    """Parse either claim shape. Returns the digest and, for v2, the burn tx hash."""
    if data.startswith(PREFIX_V2) and len(data) == len(PREFIX_V2) + 64:
        body = data[len(PREFIX_V2):]
        return {"version": 2, "digest": "0x" + body[:32].hex(), "burn_tx": "0x" + body[32:].hex()}
    if data.startswith(PREFIX) and len(data) == len(PREFIX) + 32:
        return {"version": 1, "digest": "0x" + data[len(PREFIX):].hex(), "burn_tx": None}
    raise RuntimeError("not a Quorum claim: calldata has neither the QUORUM1 nor the QUORUM2 shape")


PREFIX_REVEAL = b"QUORUM3"  # reveal: claim tx hash (32) | JSON of the claimed fields


def reveal_fields(finding: dict[str, Any]) -> dict[str, Any]:
    """Exactly the fields the claim digest was computed over, nothing more."""
    return {
        "risk": finding["risk"],
        "signature": finding["signature"],
        "contract": finding.get("contract"),
        "function": finding.get("function"),
        "corroborated_by": sorted(finding.get("seen_by", [])),
    }


def encode_reveal(claim_tx: bytes, fields: dict[str, Any]) -> bytes:
    if len(claim_tx) != 32:
        raise ValueError("claim tx hash must be 32 bytes")
    return PREFIX_REVEAL + claim_tx + json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()


def decode_reveal(data: bytes) -> dict[str, Any]:
    if not data.startswith(PREFIX_REVEAL) or len(data) <= len(PREFIX_REVEAL) + 32:
        raise RuntimeError("not a Quorum reveal: calldata is missing the QUORUM3 shape")
    body = data[len(PREFIX_REVEAL):]
    return {"claim_tx": "0x" + body[:32].hex(), "fields": json.loads(body[32:].decode())}


def reveal(finding: dict[str, Any]) -> dict[str, Any]:
    """Disclose the pattern behind an already-paid claim so other swarms can learn it.

    No second fee: the claim already burned it. What the reveal adds is
    checkability, since anyone can hash these fields and compare to the claim.
    """
    w3 = _w3()
    acct = _account(w3)
    claim_tx = bytes.fromhex(finding["attested_tx"].removeprefix("0x"))
    tx = {"from": acct.address, "to": acct.address, "value": 0,
          "data": encode_reveal(claim_tx, reveal_fields(finding)), "chainId": CHAIN_ID}
    result = _send(w3, acct, tx)
    result["url"] = EXPLORER + result["tx"]
    return result


def read_reveal(tx_hash: str) -> dict[str, Any]:
    """Read a reveal, its claim and the claim's fee burn. The three must agree."""
    _, _, tx = _find_tx(tx_hash)
    parsed = decode_reveal(bytes(tx["input"]))
    claim = read_claim(parsed["claim_tx"])
    f = parsed["fields"]
    recomputed = "0x" + claim_digest({**f, "seen_by": f.get("corroborated_by", [])}).hex().removeprefix("0x")
    burn = read_burn(claim["burn_tx"]) if claim.get("burn_tx") else None
    return {
        "fields": parsed["fields"],
        "claim_tx": parsed["claim_tx"],
        "claim": claim,
        "burn": burn,
        "revealed_by": tx["from"],
        "digest_matches": recomputed.lower() == claim["digest"].lower(),
        "same_signer": tx["from"].lower() == claim["from"].lower(),
        "fee_paid": bool(burn and burn["valid"] and burn["from"].lower() == claim["from"].lower()),
    }


def attest(finding: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """Burn the fee on Robinhood Chain, then publish the finding's digest to the claim chain."""
    w3 = _w3()
    acct = _account(w3)
    digest = claim_digest(finding)

    if dry_run:
        return {"dry_run": True, "from": acct.address, "digest": digest.hex(), "chain_id": CHAIN_ID,
                "fee": CLAIM_FEE, "token_balance": token_balance()}

    burn = burn_fee()
    tx = {
        "from": acct.address,
        "to": acct.address,
        "value": 0,
        "data": encode_claim(digest, bytes.fromhex(burn["tx"].removeprefix("0x"))),
        "chainId": CHAIN_ID,
    }
    result = _send(w3, acct, tx)
    result.update({"url": EXPLORER + result["tx"], "digest": digest.hex(), "burn": burn})
    return result


def read_claim(tx_hash: str) -> dict[str, Any]:
    """Read a published claim back off whichever chain it was written to."""
    cid, w3, tx = _find_tx(tx_hash)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    block = w3.eth.get_block(receipt["blockNumber"])
    parsed = decode_claim(bytes(tx["input"]))
    return {
        "chain_id": cid,
        "chain": chain_name(cid),
        "from": tx["from"],
        "block": receipt["blockNumber"],
        "timestamp": block["timestamp"],
        "status": receipt["status"],
        **parsed,
    }
