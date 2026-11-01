"""Stage-1 rules against a slim copy of mainnet block 26300753 (the Binance 14 delegation
block, 2026-10-29 20:20:59 UTC). No network: a fake RPC answers from recorded facts."""
import json
from pathlib import Path

from watch.replay import Ctx, evaluate_block
from watch.rules import recover_authority, rule_7702_type4

FIX = Path(__file__).parent / "fixtures" / "block-26300753-slim.json"
BINANCE_14 = "0x28c6c06298d514db089934071355e5743bf21d60"
SWEEPER = "0x63e842b054bd624a465454d533c33f573e9c6fae"
DELEGATION_TX = "0xad99264d5532ae0dd04b2004eebda05f25657e70dacb764f7ac8d4ccd051298b"


class FakeRpc:
    """Recorded on 2026-11-01 from eth.drpc.org: code sizes and the Binance 14 code flip."""
    calls = failures = 0

    def code(self, address, block="latest"):
        address = address.lower()
        if address == BINANCE_14:
            return "0x" if block == 26300752 else "0xef0100" + SWEEPER[2:]
        if address == SWEEPER:
            return "0x" + "60" * 1674
        return "0x" + "60" * 100

    def logs(self, addresses, a, b):
        return []


def block():
    return json.loads(FIX.read_text())


def test_fixture_is_the_delegation_block():
    b = block()
    assert int(b["number"], 16) == 26300753
    assert any(t["hash"] == DELEGATION_TX for t in b["transactions"])


def test_authority_recovery_matches_binance_14():
    tx = next(t for t in block()["transactions"] if t["hash"] == DELEGATION_TX)
    assert len(tx["authorizationList"]) == 50
    assert BINANCE_14 in {recover_authority(a) for a in tx["authorizationList"]}


def test_delegation_escalates_only_with_evidence():
    ctx = Ctx(FakeRpc(), {BINANCE_14: "Binance 14"})
    out = rule_7702_type4(block(), ctx)
    by_tx = {o["tx"]: o for o in out}
    hit = by_tx[DELEGATION_TX]
    assert hit["level"] == "alert"
    assert any("50 authorizations" in r for r in hit["reasons"])
    assert any("Binance 14" in r and "signed a delegation" in r for r in hit["reasons"])
    others = [o for o in out if o["tx"] != DELEGATION_TX]
    assert others and all(o["level"] == "info" for o in others)


def test_code_flip_fires_for_watched_wallet():
    ctx = Ctx(FakeRpc(), {BINANCE_14: "Binance 14"})
    alerts, timing = evaluate_block(block(), ctx)
    flips = [a for a in alerts if a["rule"] == "7702_code_flip"]
    assert len(flips) == 1 and flips[0]["subject"] == BINANCE_14
    assert SWEEPER[2:] in flips[0]["reasons"][0]
    assert set(timing) == {r.__name__ for r in __import__("watch.rules", fromlist=["RULES"]).RULES}


def test_unknown_is_not_clean():
    class DeadRpc(FakeRpc):
        def code(self, address, block="latest"):
            return None
    ctx = Ctx(DeadRpc(), {BINANCE_14: "Binance 14"})
    alerts, _ = evaluate_block(block(), ctx)
    flip = [a for a in alerts if a["rule"] == "7702_code_flip"]
    assert flip and flip[0]["unknowns"], "a failed read must surface as unknown, never as clean"
