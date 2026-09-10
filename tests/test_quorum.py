"""What must stay true for Quorum's claims to be honest."""
import os
import tempfile

from quorum.agents import LENSES
from quorum.memory import NoMemory, SwarmMemory, signature
from quorum.swarm import run_swarm

VULN = open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "VulnerableVault.sol")).read()
PROD = '''pragma solidity ^0.8.0;
contract Shares {
    mapping(address => uint256) public sharesSupply;
    function sellShares(uint256 price) external {
        (bool success1, ) = protocolFeeDestination.call{value: price}("");
        require(success1);
        sharesSupply[msg.sender] = sharesSupply[msg.sender] - price;
    }
}'''


def _db():
    return os.path.join(tempfile.mkdtemp(), "m.db")


def test_idiom_matches_across_contracts():
    assert signature("reentrancy", '(bool ok, ) = msg.sender.call{value: amt}("");') == \
           signature("reentrancy", '(bool success1, ) = feeDest.call{value: fee}("");')


def test_different_idiom_does_not_match():
    assert signature("reentrancy", '(bool ok, ) = msg.sender.call{value: amt}("");') != \
           signature("reentrancy", 'weth.deposit{value: amountETH}();')


def test_one_lens_never_confirms():
    m = SwarmMemory(_db())
    r = run_swarm(m, {"V.sol": VULN}, threshold=3)  # unreachable threshold
    assert r.promoted == [] and r.candidates


def test_two_lenses_reach_quorum():
    m = SwarmMemory(_db())
    r = run_swarm(m, {"V.sol": VULN})
    assert any(f["risk"] == "reentrancy" and len(f["seen_by"]) >= 2 for f in r.promoted)


def test_pattern_recalled_in_a_fresh_session():
    db = _db()
    run_swarm(SwarmMemory(db), {"V.sol": VULN})
    r = run_swarm(SwarmMemory(db), {"Shares.sol": PROD})   # new client, new contract
    assert any(f["risk"] == "reentrancy" for f in r.recalled)


def test_retired_findings_stay_retired():
    db = _db()
    m = SwarmMemory(db)
    run_swarm(m, {"V.sol": VULN})
    key = next(f["key"] for f in m.findings(status="confirmed"))
    assert m.retire(key, "fixture, not deployed")
    r = run_swarm(SwarmMemory(db), {"V.sol": VULN}, fresh_claims=True)
    assert r.suppressed and not r.promoted


def test_deletion_test_collapses_the_swarm():
    r = run_swarm(NoMemory(), {"V.sol": VULN})
    assert r.promoted == [] and r.recalled == [] and r.suppressed == []


def test_only_one_agent_can_hold_a_claim():
    db = _db()
    a, b = SwarmMemory(db), SwarmMemory(db)
    assert a.claim_work("Target.sol", "guard-lens", "agent-a") is True
    assert b.claim_work("Target.sol", "guard-lens", "agent-b") is False


def test_a_claim_does_not_block_a_different_unit():
    db = _db()
    a, b = SwarmMemory(db), SwarmMemory(db)
    assert a.claim_work("Target.sol", "guard-lens", "agent-a") is True
    assert b.claim_work("Target.sol", "sender-lens", "agent-b") is True


def test_recall_adds_provenance_without_rewriting_it():
    db = _db()
    run_swarm(SwarmMemory(db), {"V.sol": VULN})
    m = SwarmMemory(db)
    run_swarm(m, {"Shares.sol": PROD})
    pattern = next(p for p in m.confirmed_patterns() if p["risk"] == "reentrancy")
    assert pattern["first_confirmed_on"] == "V.sol"
    assert pattern["recognised_on"] == ["Shares.sol"]
    assert sorted(pattern["confirmed_by"]) == ["callorder-lens", "guard-lens"]
