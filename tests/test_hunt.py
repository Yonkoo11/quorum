"""find -> prove in one shot: a finder proposes candidates, the top few are settled by the prover.

No model spend and no RPC. A fake finder supplies candidates, a fake model writes the exploit, so these
tests check the wiring hunt owns: how it dedupes and ranks a finder's noise, and that it proves the top
picks and writes the proven/unproven split, reusing the same prover the single-hypothesis tool uses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import stream
from prove import hunt, tool


def test_rank_dedupes_keeps_the_most_confident_and_puts_findings_before_leads():
    found = [
        {"contract": "C", "function": "f", "confidence": 30, "tier": "finding"},
        {"contract": "C", "function": "f", "confidence": 80, "tier": "finding"},  # same key, higher
        {"contract": "C", "function": "g", "confidence": 95, "tier": "lead"},     # more confident but a lead
        {"contract": "C", "function": "", "confidence": 99, "tier": "finding"},   # no function, dropped
    ]
    ranked = hunt.rank(found, 10)
    assert [(f["function"], f["confidence"]) for f in ranked] == [("f", 80), ("g", 95)]


def test_rank_limits_to_k():
    found = [{"contract": "", "function": f"f{i}", "confidence": i, "tier": "finding"} for i in range(5)]
    assert len(hunt.rank(found, 2)) == 2


def _finder(cands):
    def run(iso):
        assert (iso / "target.sol").exists()   # hunt must hand the finder the source
        return cands, 0.5
    return run


def _model(body):
    def run(task, ws, tools, timeout=0):
        (ws / "test").mkdir(exist_ok=True)
        (ws / "test" / "Exploit.t.sol").write_text(body)
        return {"result": "done", "total_cost_usd": 1.0}
    return run


def test_find_union_samples_the_finder_and_recovers_a_flaky_finding(tmp_path, monkeypatch):
    # The generic finder is nondeterministic (1 of 5 runs surfaced the real bug on OFTSand); find_union
    # samples it several times and pools, so a finding a single run misses is still recovered.
    monkeypatch.setattr(tool, "RUNS", tmp_path / "runs")
    calls = {"n": 0}

    def flaky(iso):
        calls["n"] += 1
        if calls["n"] == 3:                      # the real finding appears on only 1 of the 4 samples
            return [{"contract": "V", "function": "approveAndCall", "confidence": 80,
                     "tier": "finding", "text": "delegate hijack"}], 0.2
        return [], 0.2

    monkeypatch.setitem(stream.CONTESTANTS, "flaky", (flaky, lambda: "flaky"))
    pooled, cost = hunt.find_union("flaky", "pragma solidity ^0.8.20;", "slug", 4)

    assert calls["n"] == 4                        # sampled every time
    assert round(cost, 2) == 0.8                  # cost summed across samples
    assert [f["function"] for f in hunt.rank(pooled, 3)] == ["approveAndCall"]  # recovered and ranked


def test_hunt_finds_ranks_and_settles_each_pick(tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(hunt, "fetch_source",
                        lambda addr, chain: ("Victim", "pragma solidity ^0.8.20;\ncontract Victim {}\n"))
    cands = [
        {"contract": "Victim", "function": "withdraw", "confidence": 90, "tier": "finding", "text": "drains ETH"},
        {"contract": "Victim", "function": "withdraw", "confidence": 40, "tier": "finding", "text": "dup, lower"},
        {"contract": "Victim", "function": "init", "confidence": 10, "tier": "lead", "text": "maybe reinit"},
        {"contract": "Victim", "function": "", "confidence": 99, "tier": "finding", "text": "no fn"},
    ]
    monkeypatch.setitem(stream.CONTESTANTS, "fake", (_finder(cands), lambda: "fake"))
    monkeypatch.setattr(stream, "claude",
                        _model("contract E { function a() external { vm.store(v,0,1); } }"))
    monkeypatch.delenv("BASE_RPC_URL", raising=False)

    report = hunt.hunt("base", "0xabc", 123, "fake", 5, "case", samples=1)

    assert report["candidates_found"] == 4
    # deduped to two, findings before leads, empty function dropped
    assert [r["function"] for r in report["results"]] == ["withdraw", "init"]
    # every settled candidate was rejected (vm.store), so nothing is proved
    assert report["proved"] == 0 and all(r["proven"] is False for r in report["results"])
    assert (tmp_path / "runs" / "case-report.json").exists()
