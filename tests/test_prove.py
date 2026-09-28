
import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prove import harness


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "PROOFS", tmp_path / "proofs")
    exploit_dir = tmp_path / "ws" / "test"
    exploit_dir.mkdir(parents=True)
    monkeypatch.delenv("BASE_RPC_URL", raising=False)
    return tmp_path / "ws"


def write(ws, body):
    (ws / "test" / "Exploit.t.sol").write_text(body)


def test_a_proof_that_rewrites_the_victim_is_rejected(ws):
    """vm.store on the fork fabricates the state the exploit needs; that is not a proof."""
    write(ws, "// exploit\ncontract E { function a() external { vm.store(victim, 0, 1); } }")
    v = harness.verdict(ws, "base")
    assert v["proven"] is False and "fabricates state" in v["reason"]


def test_an_honestly_unproven_exploit_is_not_a_pass(ws):
    write(ws, "// UNPROVEN: the flash-loan pool has no liquidity at this block\ncontract E {}")
    v = harness.verdict(ws, "base")
    assert v["proven"] is False and "unproven" in v["reason"]


def test_a_missing_exploit_is_not_a_pass(ws):
    v = harness.verdict(ws, "base")
    assert v["proven"] is False and "no Exploit" in v["reason"]


def test_a_clean_exploit_without_an_endpoint_is_unprovable_not_failed(ws):
    """No archive endpoint must read as 'cannot decide', never as a clean fail."""
    write(ws, "// exploit\ncontract E { function a() external {} }")
    v = harness.verdict(ws, "base")
    assert v["proven"] is None and "archive endpoint" in v["reason"]


def test_mockcall_is_also_forbidden(ws):
    write(ws, "contract E { function a() external { vm.mockCall(victim, x, y); } }")
    assert harness.verdict(ws, "base")["proven"] is False


def test_dealing_the_measured_token_is_rejected(ws):
    """deal(token, attacker, X) fabricates exactly the balance the scaffold measures; not a proof."""
    write(ws, "contract E { function a() external { deal(token, attacker, 1e24); } }")
    v = harness.verdict(ws, "base")
    assert v["proven"] is False and "deal()" in v["reason"]


def test_vm_deal_in_the_exploit_is_rejected(ws):
    """The scaffold funds gas; a vm.deal in the exploit itself mints the attacker native profit."""
    write(ws, "contract E { function a() external { vm.deal(attacker, 100 ether); } }")
    v = harness.verdict(ws, "base")
    assert v["proven"] is False and "deal()" in v["reason"]


def test_hoax_is_rejected_it_mints_and_pranks_in_one_call(ws):
    """hoax/startHoax deal ETH and impersonate at once, slipping past a deal-only or prank-only scan."""
    for body in ("contract E { function a() external { hoax(owner, 100 ether); v.f(); } }",
                 "contract E { function a() external { startHoax(owner); v.f(); } }"):
        write(ws, body)
        assert harness.verdict(ws, "base")["proven"] is False


def test_changeprank_to_a_non_attacker_is_rejected(ws):
    """changePrank impersonates without a vm. prefix; it must be caught like vm.startPrank."""
    write(ws, "contract E { function a() external { changePrank(owner); token.transfer(attacker,x); } }")
    v = harness.verdict(ws, "base")
    assert v["proven"] is False and "impersonates" in v["reason"]


def test_pranking_a_non_attacker_is_rejected(ws):
    """Impersonating the owner and routing funds to attacker would be a false proof."""
    write(ws, "contract E { function a() external { vm.startPrank(owner); token.transfer(attacker,x); } }")
    v = harness.verdict(ws, "base")
    assert v["proven"] is False and "impersonates" in v["reason"]


def test_pranking_the_attacker_is_allowed(ws, monkeypatch):
    """The attacker acting as themselves is the whole point; it must not trip the impostor check."""
    write(ws, "contract E { function a() external { vm.startPrank(attacker); } }")
    monkeypatch.setenv("BASE_RPC_URL", "")   # stop before forge; we only test the static gate here
    v = harness.verdict(ws, "base")
    assert "impersonates" not in v.get("reason", "")


def test_a_stream_hack_forks_from_its_own_ledger_row(tmp_path, monkeypatch):
    """Stream hacks carry chain/block/proxy from intake; a proof must fork there, not at a dev pin."""
    from bench import stream
    monkeypatch.setattr(stream, "STREAM", tmp_path / "s.json")
    stream.save({"contestants": [], "entries": [
        {"id": "NewHack", "chain": "base", "block": 999, "address": "0xIMPL", "proxy": "0xPROXY"}]})
    fork = harness.fork_of("NewHack")
    assert fork == {"chain": "base", "block": 999, "address": "0xPROXY"}
