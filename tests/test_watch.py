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


def test_live_loop_catches_up_and_persists_state(tmp_path):
    from watch.live import State, run

    class HeadRpc(FakeRpc):
        def __init__(self):
            self.heads = iter([26300753, 26300753, 26300754])
        def head(self):
            return next(self.heads, 26300754)
        def block(self, n):
            b = block(); b["number"] = hex(n); return b

    st = State(tmp_path / "state.json")
    st.last = 26300751                      # two blocks behind head
    sent = []
    run("ethereum", {BINANCE_14: "Binance 14"}, st, str(tmp_path / "log.jsonl"), sent.append,
        max_blocks=3, rpc=HeadRpc(), sleep=lambda s: None)
    assert st.last == 26300754
    assert json.loads((tmp_path / "state.json").read_text())["last_block"] == 26300754
    lines = (tmp_path / "log.jsonl").read_text().splitlines()
    assert len(lines) == 3
    assert any("Binance 14" in m and "alert only" in m for m in sent)


def test_repointing_and_bad_auth_are_not_silent():
    class RepointRpc(FakeRpc):
        def code(self, address, block="latest"):
            if address.lower() == BINANCE_14 and block == 26300752:
                return "0xef0100" + "11" * 20          # already delegated, to a different target
            return super().code(address, block)
    alerts, _ = evaluate_block(block(), Ctx(RepointRpc(), {BINANCE_14: "Binance 14"}))
    flip = [a for a in alerts if a["rule"] == "7702_code_flip"]
    assert flip and "was 0x" + "11" * 20 in flip[0]["reasons"][0]
    assert recover_authority({"chainId": "0x1", "address": "0xzz", "nonce": "0x0",
                              "yParity": "0x0", "r": "0x1", "s": "0x1"}) is None


def test_crashing_rule_becomes_unknown_alert(monkeypatch):
    import watch.replay as rp
    def boom(block, ctx): raise KeyError("input")
    monkeypatch.setattr(rp, "RULES", [boom])
    alerts, timing = evaluate_block(block(), Ctx(FakeRpc(), {}))
    assert alerts[0]["unknowns"] and "boom" in timing


def test_state_roundtrip_and_damaged_file(tmp_path):
    from watch.live import State
    st = State(tmp_path / "s.json")
    st.last = 5; st.seen = {("0xaa", ("0xbb", "0xcc"))}; st.save()
    again = State(tmp_path / "s.json")
    assert again.seen == {("0xaa", ("0xbb", "0xcc"))} and again.last == 5
    (tmp_path / "s.json").write_text("{not json")
    broken = State(tmp_path / "s.json")
    assert broken.last is None and "unreadable" in broken.note


def test_missing_block_is_notified(tmp_path):
    from watch.live import State, run

    class GapRpc(FakeRpc):
        def head(self): return 10
        def block(self, n): return None
    sent = []
    run("ethereum", {}, State(tmp_path / "s.json"), str(tmp_path / "l.jsonl"), sent.append,
        max_blocks=1, rpc=GapRpc(), sleep=lambda s: None)
    assert sent and "NOT checked" in sent[0]


def test_sweep_receipt_shows_63_transfers_out_of_binance_14():
    """Real receipt of the Binance 14 sweep tx (block 26300770), recorded 2026-11-01."""
    from watch.simulate import _transfers_out
    rcpt = json.loads((FIX.parent / "sweep-receipt-26300770.json").read_text())
    out = _transfers_out(rcpt, {BINANCE_14: "Binance 14"})
    assert len(out) == 63 and all(o["to"] == "0x5227f603c1ee34ce3c06efe6477003bdfccb2f8c" for o in out)


def test_live_attaches_simulation_to_tx_alerts(tmp_path):
    from watch.live import State, run

    class AdminRpc(FakeRpc):
        def head(self): return 26300753
        def block(self, n):
            b = block()
            b["transactions"].append({"hash": "0xadmin", "from": "0xbad", "to": BINANCE_14,
                                      "type": "0x2", "input": "0xf2fde38b" + "00" * 32})
            return b
    calls = []
    def fake_sim(chain, tx, watch):
        calls.append(tx); return {"seconds": 1.0, "funds_left": True, "eth_delta": {"Binance 14": -1.0},
                                  "transfers_out": [], "unknown": None}
    sent = []
    run("ethereum", {BINANCE_14: "Binance 14"}, State(tmp_path / "s.json"), str(tmp_path / "l.jsonl"),
        sent.append, max_blocks=1, rpc=AdminRpc(), sleep=lambda s: None, simulate=fake_sim)
    assert calls == ["0xadmin"], "only the admin call is simulated; the delegation tx is not"
    assert any("funds left = True" in m for m in sent)


def test_replay_failure_and_urls_never_reach_the_alert(tmp_path):
    from watch.live import State, run
    from watch.simulate import redact

    class AdminRpc(FakeRpc):
        def head(self): return 26300753
        def block(self, n):
            b = block()
            b["transactions"].append({"hash": "0xadmin", "from": "0xbad", "to": BINANCE_14,
                                      "type": "0x2", "input": "0xf2fde38b" + "00" * 32})
            return b
    def boom(chain, tx, watch): raise RuntimeError("https://rpc.example/key123 down")
    sent = []
    run("ethereum", {BINANCE_14: "Binance 14"}, State(tmp_path / "s.json"), str(tmp_path / "l.jsonl"),
        sent.append, max_blocks=1, rpc=AdminRpc(), sleep=lambda s: None, simulate=boom)
    assert any(m.startswith("[Quorum watch] watchlist_admin_call") for m in sent), "the alert itself still went out"
    assert any("replay UNKNOWN: replay raised RuntimeError" in m for m in sent)
    assert "key123" not in "".join(sent)
    assert redact("eth_call: https://rpc.example/key123 refused") == "eth_call: <url> refused"
