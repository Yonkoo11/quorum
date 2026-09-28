"""The public prove tool: point the proof engine at a contract the caller chooses.

No model spend and no RPC here. A fake `fetch_source` supplies canned victim source and a fake model
writes the exploit, so these tests check the tool's own plumbing: the workspace it assembles, the task
it hands the model, and that the same anti-fakery guards fire through this path as through the
benchmark path.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prove import tool


@pytest.fixture
def runs(tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(tool, "fetch_source",
                        lambda addr, chain: ("Victim", "pragma solidity ^0.8.20;\ncontract Victim {}\n"))
    monkeypatch.delenv("BASE_RPC_URL", raising=False)
    return tmp_path


def fake_model(writes):
    """A stand-in for stream.claude that drops `writes` into the workspace's Exploit.t.sol."""
    def run(task, ws, tools, timeout=0):
        (ws / "test").mkdir(exist_ok=True)
        (ws / "test" / "Exploit.t.sol").write_text(writes)
        return {"result": "done", "total_cost_usd": 0.0}
    return run


def test_build_assembles_the_workspace_from_the_hypothesis(runs):
    ws = tool.build("base", "0xabc0000000000000000000000000000000000000", 27_000_000,
                    None, "swapV3", "free-mint moves the pool price", "case-1")
    assert (ws / "target" / "victim.sol").read_text().startswith("pragma solidity")
    task = (ws / "TASK.md").read_text()
    assert "swapV3" in task and "27000000" in task and "base" in task
    assert "free-mint moves the pool price" in task
    assert "0xabc0000000000000000000000000000000000000" in task


def test_an_unknown_chain_is_refused(runs):
    with pytest.raises(SystemExit):
        tool.build("solana", "0xabc", 1, None, "f", "a", "case")


def test_a_state_faking_proof_is_rejected_through_the_tool(runs, monkeypatch):
    """vm.store fabricates the fork state; the tool must reject it exactly as the benchmark does."""
    monkeypatch.setattr(tool.stream, "claude",
                        fake_model("contract E { function a() external { vm.store(victim,0,1); } }"))
    rec = tool.prove("base", "0xabc", 1, None, "a", "drain via fake slot", "faker")
    assert rec["proven"] is False and "fabricates state" in rec["reason"]
    assert (runs / "runs" / "faker" / "result.json").exists()


def test_an_honestly_unproven_run_is_recorded_not_passed(runs, monkeypatch):
    monkeypatch.setattr(tool.stream, "claude",
                        fake_model("// UNPROVEN: the pool has no liquidity at this block\ncontract E {}"))
    rec = tool.prove("base", "0xabc", 1, None, "a", "attack", "honest")
    assert rec["proven"] is False and "unproven" in rec["reason"]


def test_check_reproduces_from_the_saved_workspace(runs, monkeypatch):
    monkeypatch.setattr(tool.stream, "claude",
                        fake_model("contract E { function a() external { vm.mockCall(victim,x,y); } }"))
    tool.prove("base", "0xabc", 1, None, "a", "attack", "recheck")
    v = tool.check(str(runs / "runs" / "recheck"))
    assert v["proven"] is False
