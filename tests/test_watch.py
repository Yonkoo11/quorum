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
    assert hit["acted"] == [BINANCE_14] == hit["watched"], "the real hack: the watched key signed, so urgent"
    others = [o for o in out if o["tx"] != DELEGATION_TX]
    assert others and all(o["level"] == "info" and o["watched"] == [] == o["acted"] for o in others)


def test_replayed_authorization_is_not_urgent():
    """Anyone can copy Binance 14's signed authorization into their own tx; the chain skips the
    stale nonce, so the wallet's code never changes. Alert, but not urgent (review 2026-11-01)."""
    b = block()
    real = next(t for t in b["transactions"] if t["hash"] == DELEGATION_TX)
    replay = {**real, "hash": "0x" + "ee" * 32, "from": "0x" + "ab" * 20, "to": "0x" + "ab" * 20}
    b["transactions"] = [replay]

    class UnchangedRpc(FakeRpc):
        def code(self, address, block="latest"):
            return "0x" if address.lower() == BINANCE_14 else super().code(address, block)
    out = rule_7702_type4(b, Ctx(UnchangedRpc(), {BINANCE_14: "Binance 14"}))
    assert len(out) == 1 and out[0]["level"] == "alert"
    assert out[0]["watched"] == [BINANCE_14] and out[0]["acted"] == []
    assert any("replayed" in r for r in out[0]["reasons"])

    class DeadRpc(FakeRpc):
        def code(self, address, block="latest"):
            return None
    out = rule_7702_type4(b, Ctx(DeadRpc(), {BINANCE_14: "Binance 14"}))
    assert out[0]["acted"] == [] and out[0]["watched"] == [BINANCE_14] and out[0]["unknowns"]

    class AlreadyRpc(FakeRpc):   # the delegation is already in place: the code matches at n-1 and n
        def code(self, address, block="latest"):
            return "0xef0100" + SWEEPER[2:] if address.lower() == BINANCE_14 else super().code(address, block)
    out = rule_7702_type4(b, Ctx(AlreadyRpc(), {BINANCE_14: "Binance 14"}))
    assert out[0]["acted"] == [] and any("replayed" in r for r in out[0]["reasons"])


def test_cleared_delegation_counts_as_acted(monkeypatch):
    """A watched wallet signing the zero-address delegate clears its code: that is the wallet acting."""
    import watch.rules as rules
    monkeypatch.setattr(rules, "recover_authority", lambda a: BINANCE_14)
    b = block()
    b["transactions"] = [{"hash": "0x" + "ee" * 32, "type": "0x4", "from": "0x" + "ab" * 20, "to": "0x" + "ab" * 20,
                          "authorizationList": [{"address": rules.ZERO_ADDRESS}]}]

    class ClearRpc(FakeRpc):
        def code(self, address, block="latest"):
            if address.lower() == BINANCE_14:
                return "0xef0100" + SWEEPER[2:] if block == 26300752 else "0x"
            return super().code(address, block)
    ctx = Ctx(ClearRpc(), {BINANCE_14: "Binance 14"})
    out = rules.rule_7702_type4(b, ctx)
    assert out[0]["acted"] == [BINANCE_14] and out[0]["level"] == "alert"
    flips = rules.rule_7702_code_flip(b, ctx)
    assert len(flips) == 1 and flips[0]["acted"] == [BINANCE_14] and "cleared" in flips[0]["reasons"][0]
    assert rules.rule_7702_code_flip(block(), Ctx(FakeRpc(), {SWEEPER: "contract"})) == [], "contracts are skipped"


def test_code_flip_fires_for_watched_wallet():
    ctx = Ctx(FakeRpc(), {BINANCE_14: "Binance 14"})
    alerts, timing = evaluate_block(block(), ctx)
    flips = [a for a in alerts if a["rule"] == "7702_code_flip"]
    assert len(flips) == 1 and flips[0]["subject"] == BINANCE_14 and flips[0]["acted"] == [BINANCE_14]
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


ZERO = "0x" + "00" * 20


def type4_block(delegate, n_auths):
    auth = {"chainId": "0x1", "address": delegate, "nonce": "0x0", "yParity": "0x0", "r": "0x1", "s": "0x1"}
    tx = {"hash": "0xt4", "from": "0xsender", "to": "0xsender", "type": "0x4", "authorizationList": [auth] * n_auths}
    return {"number": "0x10", "timestamp": "0x0", "transactions": [tx]}


def test_zero_address_delegate_is_a_clear_not_an_alert():
    """Live run 2026-11-01: 4 of 7 alerts were wallets clearing a delegation (EIP-7702: zero address clears)."""
    class ZeroRpc(FakeRpc):
        def code(self, address, block="latest"):
            return "0x" if address == ZERO else super().code(address, block)
    out = rule_7702_type4(type4_block(ZERO, 1), Ctx(ZeroRpc(), {}))
    assert out[0]["level"] == "info" and any("delegation cleared" in r for r in out[0]["reasons"])
    assert not any("NO code" in r for r in out[0]["reasons"])


def test_big_batch_to_a_real_contract_is_info_but_empty_delegate_still_alerts():
    out = rule_7702_type4(type4_block("0x" + "ab" * 20, 7), Ctx(FakeRpc(), {}))
    assert out[0]["level"] == "info" and any("7 authorizations in one tx" in r for r in out[0]["reasons"])

    class EmptyRpc(FakeRpc):
        def code(self, address, block="latest"): return "0x"
    out = rule_7702_type4(type4_block("0x" + "cd" * 20, 1), Ctx(EmptyRpc(), {}))
    assert out[0]["level"] == "alert" and "delegate without code" in out[0]["reasons"]


def test_notifier_spaces_caps_digests_and_dedupes():
    from watch.live import format_alert
    from watch.notify import Notifier
    now, sent, naps = [1000.0], [], []
    n = Notifier(sent.append, clock=lambda: now[0], sleep=naps.append, per_minute=20, dedupe_seconds=600)
    n("a"); now[0] += 0.25; n("b")
    assert naps == [0.75], "second message waits for the 1 s gap"
    for i in range(25):
        n(f"msg {i}")
    assert len(sent) == 20 and len(n.held) == 7, "the 20/min cap holds the overflow"
    assert n.flush() is False, "no room in the minute yet"
    now[0] += 61
    assert n.flush() and sent[-1].startswith("[Quorum watch] digest 1/1: 7 message(s)") and "msg 24" in sent[-1]
    al = {"rule": "7702_code_flip", "block": 5, "tx": None, "subject": BINANCE_14, "reasons": ["x"], "unknowns": []}
    assert n(format_alert("ethereum", al)) is True
    assert n(format_alert("ethereum", al)) is False and n.stats["suppressed"] == 1, "byte-identical repeat"
    al["block"] = 6
    assert n(format_alert("ethereum", al)) is True, "same sender, new block: a new message, never hidden"
    al["tx"] = "0x" + "ee" * 32
    assert n(format_alert("ethereum", al)) is True, "same sender, new tx: sent"
    now[0] += 601
    al["block"] = 5; al["tx"] = None
    assert n(format_alert("ethereum", al)) is True, "after the window the same alert goes out again"
    assert "suppressed" in n.summary()


def test_notifier_digest_puts_watchlist_first_never_drops_and_marks_cuts():
    from watch.live import _send, format_alert
    from watch.notify import TELEGRAM_MAX, Notifier, fit
    now, sent = [0.0], []
    n = Notifier(sent.append, clock=lambda: now[0], sleep=lambda s: None, per_minute=3)
    for i in range(3):
        n(f"fill {i}")
    base = {"rule": "7702_type4", "tx": None, "unknowns": [], "block": 7, "acted": []}
    for i in range(30):   # noise anyone can make: a reason naming the address, or a tx sent TO it
        noise = {**base, "subject": f"0x{'ab' * 20}", "watched": [BINANCE_14] if i % 2 else [],
                 "reasons": [f"sent to watched Binance 14; delegate {BINANCE_14} " + "x" * 600]}
        _send(n, f"noise {i} " + format_alert("ethereum", noise), noise)
    batch = {**base, "subject": f"0x{'cd' * 20}", "watched": [BINANCE_14], "acted": [BINANCE_14],
             "reasons": [f"watched wallet Binance 14 ({BINANCE_14}) signed a delegation"]}   # the watched key signed
    _send(n, format_alert("ethereum", batch), batch)
    assert len(n.held) == 31 and n.held[-1][0] is True and not any(u for u, _ in n.held[:-1]), \
        "only an alert where the watched address itself acted is urgent"
    now[0] += 61
    assert n.flush() is True
    digests = [s for s in sent if s.startswith("[Quorum watch] digest")]
    assert len(digests) == 3 and all(len(d) <= TELEGRAM_MAX for d in digests), "this minute takes 3 posts"
    assert "signed a delegation" in digests[0] and digests[0].index("signed a delegation") < digests[0].index("noise"), \
        "the watched-wallet batch goes first, ahead of noise that merely mentions the address"
    assert digests[0].startswith("[Quorum watch] digest 1/")
    assert n.held and all(m.startswith("noise") and not u for u, m in n.held), "the rest waits, nothing dropped"
    total = sum(d.count("noise ") for d in digests) + len(n.held)
    assert total == 30
    big = fit("y" * 5000)
    assert len(big) == TELEGRAM_MAX and big.endswith("[cut: message was 5000 characters; full text in the jsonl log]")


def test_zcash_reader_unknown_on_regtest_and_catches_inflation():
    from watch.zcash import MAX_BLOCK_SUBSIDY_ZAT, check, parse_info
    info = json.loads((Path(__file__).parent / "fixtures" / "zebra-regtest-getblockchaininfo.json").read_text())["result"]
    cur = parse_info(info)
    assert cur["unknown"] == f"node not synced: height 0 of about {info['estimatedheight']}"
    out = check(None, cur)
    assert out[0]["level"] == "unknown" and out[0]["rule"] == "zcash_supply" and "NOT checked" in out[0]["reasons"][0]
    synced = dict(info, blocks=3_000_000, estimatedheight=3_000_001)
    for p in synced["valuePools"]:
        p["chainValueZat"] = 1_000_000 * 10**8
    synced["chainSupply"] = {"chainValueZat": 6_000_000 * 10**8}
    prev = parse_info(synced)
    assert "unknown" not in prev and check(None, prev)[0]["level"] == "info"
    nxt = dict(prev, height=prev["height"] + 10, supply=prev["supply"] + 10 * MAX_BLOCK_SUBSIDY_ZAT,
               pools=dict(prev["pools"], transparent=prev["pools"]["transparent"] + 10 * MAX_BLOCK_SUBSIDY_ZAT))
    assert check(prev, nxt)[0]["level"] == "info", "10 blocks x 12.5 ZEC is allowed"
    nxt["supply"] += 1; nxt["pools"]["transparent"] += 1
    out = check(prev, nxt)
    assert out[0]["level"] == "alert" and "supply rose" in out[0]["reasons"][0]
    bad = dict(prev, supply=prev["supply"] - 5)
    assert "chainSupply says" in check(None, bad)[0]["reasons"][0]
    assert check(prev, dict(prev, height=prev["height"] - 1))[0]["reasons"][0].startswith("height fell")
    assert check(None, parse_info(dict(synced, valuePools=synced["valuePools"][:5])))[0]["unknowns"] == ["pools missing: ironwood"]


def test_drift_detects_change_and_never_calls_no_drift_on_failure():
    from watch.drift import check, parse_facts, report
    facts = parse_facts(Path("watch/zcash-facts.md").read_text())
    assert [f["id"] for f in facts] == ["zebra-latest-release", "zebra-advisories-page-1",
                                         "zebra-value-pool-ids", "zebra-max-block-subsidy"]
    pages = {
        facts[0]["upstream"]: "# Changelog\n\n## [Zebra 7.0.0](x) - 2026-10-22\n## [Zebra 7.0.0-rc.0](y)\n",
        facts[2]["upstream"]: "\n".join(f'Self::new_internal("{p}", amount, delta)'
                                        for p in ("transparent", "sprout", "sapling", "orchard", "lockbox", "ironwood")),
        facts[3]["upstream"]: "pub(crate) const MAX_BLOCK_SUBSIDY: u64 = ((25 * COIN) / 2) as u64;\n",
    }
    def fake(url):
        if url not in pages:
            raise OSError("offline")
        return pages[url]
    rows = check(facts, fake)
    assert [r.get("drift") for r in rows] == [False, None, False, False] and rows[1]["unknown"] == "offline"
    code, lines = report(rows)
    assert code == 2 and lines[1].startswith("[Quorum drift] UNKNOWN zebra-advisories-page-1")
    pages[facts[0]["upstream"]] = "## [Zebra 7.1.0](x) - 2026-12-01\n"
    pages[facts[2]["upstream"]] += '\nSelf::new_internal("newpool", amount, delta)'
    rows = check(facts[:1] + facts[2:3], fake)
    assert rows[0]["drift"] and rows[0]["current"] == "7.1.0" and rows[1]["drift"] and "newpool" in rows[1]["current"]
    assert report(rows)[0] == 1
    rows = check([dict(facts[0], upstream="https://example.com/x")], fake)
    assert "host not allowed" in rows[0]["unknown"]
    pages[facts[3]["upstream"]] = "nothing here"
    assert check(facts[3:], fake)[0]["unknown"] == "extract pattern matched nothing"


def test_heartbeat_reports_blocks_and_alerts(tmp_path):
    from watch.live import State, run

    class HeadRpc(FakeRpc):
        n = 26300752
        def head(self): self.n += 1; return self.n
        def block(self, n): return block()
    now = [0.0]
    def clock():
        now[0] += 30; return now[0]
    sent = []
    run("ethereum", {BINANCE_14: "Binance 14"}, State(tmp_path / "s.json"), str(tmp_path / "l.jsonl"),
        sent.append, max_blocks=3, rpc=HeadRpc(), sleep=lambda s: None, heartbeat_seconds=60, clock=clock)
    beats = [m for m in sent if "heartbeat" in m]
    assert beats and "alert(s)" in beats[0] and "blocks in" in beats[0]


def test_telegram_429_waits_retry_after_and_retries_once(monkeypatch):
    import io, urllib.error, urllib.request
    from watch import live
    monkeypatch.setenv("QUORUM_WATCH_TG_TOKEN", "t"); monkeypatch.setenv("QUORUM_WATCH_TG_CHAT", "c")
    calls, naps = [], []
    class Ok:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def fake_open(req, timeout):
        calls.append(req)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {},
                                         io.BytesIO(b'{"ok":false,"parameters":{"retry_after":3}}'))
        return Ok()
    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    assert live.post_telegram("hi", sleep=naps.append) is True
    assert naps == [3] and len(calls) == 2


def test_range_pass_reads_code_and_logs_over_the_span(tmp_path):
    """Range mode (fast chains): one pass covers every block since the last one, code is compared
    with the remembered value (no old state is ever read: the public Arbitrum RPC keeps 64 blocks),
    logs are read in 100-block pieces, no block body is fetched, the record says which rules did
    not run, and the new code is saved for the next pass."""
    from watch.live import State, run
    seen_logs = []

    class RangeRpc(FakeRpc):
        def head(self):
            return 350
        def header(self, n):
            return {"number": hex(n), "timestamp": hex(1_700_000_000 + n)}
        def block(self, n):
            raise AssertionError("range mode must never fetch transaction bodies")
        def code(self, address, block="latest"):
            if block != 350:
                return None                                   # old state: the endpoint refuses it
            return "0xef0100" + SWEEPER[2:] if address.lower() == BINANCE_14 else "0x" + "60" * 100
        def logs(self, addresses, a, b):
            seen_logs.append((a, b)); return []

    (tmp_path / "state.json").write_text(json.dumps({"last_block": 100, "codes": {BINANCE_14: "0x"}}))
    st = State(tmp_path / "state.json")
    sent = []
    run("ethereum", {BINANCE_14: "Binance 14"}, st, str(tmp_path / "log.jsonl"), sent.append,
        max_blocks=1, rpc=RangeRpc(), sleep=lambda s: None, range_mode=True, catch_up=5000)
    lines = [json.loads(l) for l in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert len(lines) == 1 and lines[0]["blocks"] == [101, 350] and lines[0]["span"] == 250
    assert seen_logs == [(101, 200), (201, 300), (301, 350)]
    flips = [a for a in lines[0]["alerts"] if a["rule"] == "7702_code_flip"]
    assert flips and flips[0]["acted"] == [BINANCE_14] and not flips[0]["unknowns"]
    assert "between blocks 101 and 350" in flips[0]["reasons"][0]
    assert any("not read" in u for u in lines[0]["unknowns"])
    assert st.last == 350
    saved = json.loads((tmp_path / "state.json").read_text())
    assert saved["codes"][BINANCE_14] == "0xef0100" + SWEEPER[2:]
    assert any("Binance 14" in m and "between blocks 101 and 350" in m for m in sent)


def test_unreadable_code_is_info_until_three_passes_then_one_alert():
    """Measured 2026-11-07: 3.5% of Arbitrum passes could not read code, in bursts, every re-probe
    fine; one alert per miss buried the real ones. Now: retry at the head, info row with the RPC's
    own error (URL stripped), one alert on the third miss in a row, reset on a good read."""
    class FlakyRpc(FakeRpc):
        last_error = "eth_getCode: header not found https://rpc.example/secret-key"
        def code(self, address, block="latest"):
            return None
    ctx = Ctx(FlakyRpc(), {BINANCE_14: "Binance 14"})
    levels = []
    for _ in range(4):
        alerts, _ = evaluate_block(block(), ctx)
        flip = [a for a in alerts if a["rule"] == "7702_code_flip"]
        assert flip and flip[0]["unknowns"], "a failed read must surface as unknown, never as clean"
        levels.append(flip[0]["level"])
    assert levels == ["info", "info", "alert", "info"]
    assert "header not found" in flip[0]["unknowns"][0] and "https://" not in flip[0]["unknowns"][0]
    assert "4 pass(es) in a row" in flip[0]["reasons"][0]

    class HeadLag(FakeRpc):          # the block read fails, the head read works: a checked pass
        def code(self, address, block="latest"):
            return ("0xef0100" + SWEEPER[2:]) if block == "latest" else None
    ctx = Ctx(HeadLag(), {BINANCE_14: "Binance 14"}, {BINANCE_14: "0x"})
    alerts, _ = evaluate_block(block(), ctx)
    flip = [a for a in alerts if a["rule"] == "7702_code_flip"]
    assert [f["level"] for f in flip] == ["info", "alert"] and flip[1]["acted"] == [BINANCE_14]   # noted, then the real flip
    assert "read at the head" in flip[0]["unknowns"][0] and ctx.unread == {}
    alerts, _ = evaluate_block(block(), ctx)                  # same code again: the head-only read is still on record
    flip = [a for a in alerts if a["rule"] == "7702_code_flip"]
    assert [f["level"] for f in flip] == ["info"]

    from watch.rpc import redact                               # the configured endpoint never reaches a log, URL or not
    assert redact("boom key=abcdefghijkl at wss://h/abcdefghijkl", "abcdefghijkl") == "boom key=<endpoint> at <url>"


def test_fetch_failures_log_the_rpc_error(tmp_path):
    """A head/block fetch failure now records the endpoint's own error (URL stripped) in the log row."""
    from watch.live import State, run

    class DeadHead(FakeRpc):
        last_error = "eth_blockNumber: timed out https://rpc.example/k"
        def head(self):
            return None

    class Stop(Exception):
        pass

    def sleep(_):
        raise Stop
    try:
        run("ethereum", {}, State(tmp_path / "s.json"), str(tmp_path / "log.jsonl"), print,
            max_blocks=1, rpc=DeadHead(), sleep=sleep)
    except Stop:
        pass
    row = json.loads((tmp_path / "log.jsonl").read_text().splitlines()[0])
    assert row["unknown"] == "head fetch failed" and "timed out" in row["error"] and "https://" not in row["error"]


def test_prover_starts_once_per_upgrade_capped_and_reports_the_finish(tmp_path):
    """Stage 5: an Upgraded event emitted by a watched contract starts prove/hunt.py on it at that
    block, in the background; the alert went out first. One run per contract per day, a daily cap,
    the finished run's own summary line is reported on the next poll, a crash reports the exit code."""
    from watch.live import Prover
    UPG = "0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b"
    A, B, C = "0x" + "a1" * 20, "0x" + "b2" * 20, "0x" + "c3" * 20
    spawned, sent = [], []

    class Proc:
        def __init__(self, cmd, stdout):
            self.cmd, self.out, self.code = cmd, stdout, None
        def poll(self):
            return self.code

    def spawn(cmd, stdout, stderr):
        spawned.append(Proc(cmd, stdout)); return spawned[-1]

    def upgraded(addr, block):
        return {"rule": "watchlist_admin_event", "level": "alert", "block": block, "subject": addr,
                "reasons": [f"X: Upgraded emitted"], "unknowns": [], "watched": [addr], "acted": [addr]}

    pv = Prover("arbitrum", sent.append, max_per_day=2, spawn=spawn, clock=lambda: 1_700_000_000,
                log_dir=str(tmp_path / "hunts"), python="py")
    pv.consider(upgraded(A, 500))
    assert spawned[0].cmd == ["py", "-m", "prove.hunt", "arbitrum", A, "--block", "500", "--name", f"watch-arbitrum-{A[:10]}-500"]
    assert sent[-1].startswith(f"[Quorum watch] prover started on {A} (arbitrum block 500)")
    pv.consider(upgraded(A, 501))                       # same contract, same day: no second run
    assert len(spawned) == 1 and "already ran today" in sent[-1]
    pv.consider({**upgraded(B, 502), "reasons": ["X: RoleGranted emitted"]})   # not a code change
    pv.consider({**upgraded(B, 502), "acted": [], "reasons": ["could not read logs"]})
    assert len(spawned) == 1
    pv.consider(upgraded(B, 503)); pv.consider(upgraded(C, 504))
    assert len(spawned) == 2 and "cap" in sent[-1] and C in sent[-1]
    pv.reap(); assert len(pv.jobs) == 2                 # still running: nothing reported
    spawned[0].out.write("target: Vault\n=== Vault: 1 proven of 3 tried, 7 found. report: r.json ===\n  PROVEN Vault.withdraw\n")
    spawned[0].out.flush(); spawned[0].code = 0
    spawned[1].out.write("Traceback\nRuntimeError: no RPC https://x.y/key\n"); spawned[1].out.flush(); spawned[1].code = 1
    pv.reap()
    assert any(m.startswith(f"[Quorum watch] prover finished on {A}: Vault: 1 proven of 3 tried") for m in sent)
    fail = [m for m in sent if "prover FAILED" in m]
    assert fail and B in fail[0] and "exit 1" in fail[0] and "https://" not in fail[0]
    assert pv.jobs == [] and pv.reap() is None          # reported once
