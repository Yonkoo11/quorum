"""Stage-1 rules: no model, one block in, zero or more alerts out.

Each rule is a function (block, ctx) -> list[dict]. `ctx` carries the Rpc,
the watchlist (lowercase addresses -> label) and a per-block cache.
An alert is a plain dict with: rule, version, block, tx, subject, reasons, unknowns.
"unknowns" lists every fact the rule needed but could not fetch.
"""
from __future__ import annotations

DELEGATION_PREFIX = "0xef0100"          # EIP-7702: code = 0xef0100 || address
TYPE_SET_CODE = "0x4"                   # EIP-7702 transaction type
ZERO_ADDRESS = "0x" + "00" * 20         # as a 7702 delegate it clears the delegation (spec)

# Admin-shaped function selectors (first 4 bytes of calldata).
ADMIN_SELECTORS = {
    "0xf2fde38b": "transferOwnership(address)",
    "0x3659cfe6": "upgradeTo(address)",
    "0x4f1ef286": "upgradeToAndCall(address,bytes)",
    "0x2f2ff15d": "grantRole(bytes32,address)",
    "0xd547741f": "revokeRole(bytes32,address)",
    "0x8f283970": "changeAdmin(address)",
    "0x8456cb59": "pause()",
    "0x3f4ba83a": "unpause()",
}
# Admin-shaped event topics (keccak of the canonical signature).
ADMIN_TOPICS = {
    "0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0": "OwnershipTransferred",
    "0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b": "Upgraded",
    "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d": "RoleGranted",
    "0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b": "RoleRevoked",
    "0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f": "AdminChanged",
}


BATCH_AUTHS = 5                         # measured: ordinary type-4 txs carry 1 (2026-11-01, 123 of 125 seen)

try:  # authority recovery needs the signing libraries web3 ships with; optional
    import rlp
    from eth_keys import keys as _keys
    from eth_utils import keccak as _keccak
except ImportError:  # pragma: no cover
    rlp = _keys = _keccak = None


def _alert(rule: str, block: dict, tx: dict | None, subject: str, reasons: list, unknowns=(), level="alert"):
    return {
        "rule": rule, "version": 2, "level": level,
        "block": int(block["number"], 16), "block_ts": int(block["timestamp"], 16),
        "tx": tx["hash"] if tx else None, "subject": subject.lower(),
        "reasons": reasons, "unknowns": list(unknowns),
    }


def recover_authority(auth: dict) -> str | None:
    """EIP-7702: authority = ecrecover(keccak(0x05 || rlp([chain_id, address, nonce])), sig)."""
    if _keys is None:
        return None
    try:  # any malformed field (attacker-controlled bytes) is reported as unknown, never raised
        msg = _keccak(b"\x05" + rlp.encode([int(auth["chainId"], 16),
                                            bytes.fromhex(auth["address"][2:]), int(auth["nonce"], 16)]))
        sig = _keys.Signature(vrs=(int(auth["yParity"], 16), int(auth["r"], 16), int(auth["s"], 16)))
        return sig.recover_public_key_from_msg_hash(msg).to_address().lower()
    except Exception:
        return None


def _delegate_facts(delegates: list, ctx, reasons: list, unknowns: list) -> bool:
    """Append code facts per delegate; True when any real delegate has no code.
    The zero address is the spec's way to clear a delegation (EIP-7702), not a target."""
    empty = False
    for d in delegates:
        if d == ZERO_ADDRESS:
            reasons.append("delegation cleared (zero-address delegate)")
            continue
        code = ctx.cached_code(d)
        if code is None:
            unknowns.append(f"code of delegate {d}")
        elif code == "0x":
            reasons.append(f"delegate {d} has NO code")
            empty = True
        else:
            reasons.append(f"delegate {d} has code ({(len(code) - 2) // 2} bytes)")
    return empty


def rule_7702_type4(block: dict, ctx) -> list:
    """Every type-4 tx is logged (info). It becomes an alert when: a watched wallet is the
    authority or the recipient, or a delegate with no code. A big batch alone stays info:
    live run 2026-11-01, 84 blocks: every batch alert was an ordinary batcher (~250/day)."""
    out = []
    for tx in block.get("transactions", []):
        if tx.get("type") != TYPE_SET_CODE:
            continue
        auths = tx.get("authorizationList") or []
        reasons = [f"type-4 transaction with {len(auths)} authorization(s)"]
        unknowns, escalate = [], []
        if _delegate_facts(sorted({a["address"].lower() for a in auths}), ctx, reasons, unknowns):
            escalate.append("delegate without code")
        pair = (tx["from"].lower(), tuple(sorted({a["address"].lower() for a in auths})))
        if len(auths) >= BATCH_AUTHS and pair not in ctx.seen_batches:
            ctx.seen_batches.add(pair)             # first batch from this sender: worth a line, not an alert
            reasons.append(f"{len(auths)} authorizations in one tx (first batch from this sender)")
        if (tx.get("to") or "").lower() in ctx.watchlist:
            escalate.append(f"sent to watched {ctx.watchlist[tx['to'].lower()]}")
        authorities = {recover_authority(a) for a in auths}
        if None in authorities:
            unknowns.append("authority of one or more authorizations (recovery unavailable)")
        for who in sorted(a for a in authorities if a and a in ctx.watchlist):
            escalate.append(f"watched wallet {ctx.watchlist[who]} ({who}) signed a delegation")
        level = "alert" if escalate else "info"
        out.append(_alert("7702_type4", block, tx, tx["from"], reasons + escalate, unknowns, level))
    return out


def rule_7702_code_flip(block: dict, ctx) -> list:
    """Watched wallet whose 7702 pointer appears or changes in this block (re-pointing counts)."""
    out = []
    n = int(block["number"], 16)
    for addr, label in ctx.watchlist.items():
        now = ctx.rpc.code(addr, n)
        if now is None:
            out.append(_alert("7702_code_flip", block, None, addr,
                              ["could not read code"], [f"code of {addr} at {n}"]))
            continue
        if not now.startswith(DELEGATION_PREFIX):
            continue
        before = ctx.rpc.code(addr, n - 1)
        if before is None or before != now:
            was = "unknown" if before is None else ("none" if before == "0x" else f"0x{before[8:]}")
            out.append(_alert("7702_code_flip", block, None, addr,
                              [f"{label}: 7702 pointer is now 0x{now[8:]} (was {was})"],
                              [] if before is not None else [f"code of {addr} at {n - 1}"]))
    return out


def rule_watchlist_admin_call(block: dict, ctx) -> list:
    """A tx to a watched contract calling an admin-shaped selector."""
    out = []
    for tx in block.get("transactions", []):
        to = (tx.get("to") or "").lower()
        if to not in ctx.watchlist:
            continue
        sel = (tx.get("input") or "")[:10]
        if sel in ADMIN_SELECTORS:
            out.append(_alert("watchlist_admin_call", block, tx, to,
                              [f"{ctx.watchlist[to]}: {ADMIN_SELECTORS[sel]} called by {tx['from']}"]))
    return out


def rule_watchlist_admin_event(block: dict, ctx) -> list:
    """An admin-shaped event emitted by a watched contract (catches calls via proxies/multisigs)."""
    n = int(block["number"], 16)
    logs = ctx.rpc.logs(list(ctx.watchlist), n, n) if ctx.watchlist else []
    if logs is None:
        return [_alert("watchlist_admin_event", block, None, "*",
                       ["could not read logs"], [f"logs at {n}"])]
    out = []
    for lg in logs:
        topic = (lg.get("topics") or [""])[0]
        if topic in ADMIN_TOPICS:
            addr = lg["address"].lower()
            out.append(_alert("watchlist_admin_event", block, {"hash": lg["transactionHash"]}, addr,
                              [f"{ctx.watchlist[addr]}: {ADMIN_TOPICS[topic]} emitted"]))
    return out


def rule_deploy_targets_watchlist(block: dict, ctx) -> list:
    """Contract creation whose init code embeds a watched address (attacker preparation signal)."""
    out = []
    for tx in block.get("transactions", []):
        if tx.get("to") is not None:
            continue
        data = (tx.get("input") or "").lower()
        hits = [label for a, label in ctx.watchlist.items() if a[2:] in data]
        if hits:
            out.append(_alert("deploy_targets_watchlist", block, tx, tx["from"],
                              [f"new contract from {tx['from']} embeds watched address(es): {', '.join(hits)}"]))
    return out


RULES = [
    rule_7702_type4,
    rule_7702_code_flip,
    rule_watchlist_admin_call,
    rule_watchlist_admin_event,
    rule_deploy_targets_watchlist,
]
