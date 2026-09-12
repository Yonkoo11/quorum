"""What must stay true for Quorum's claims to be honest."""
import os
import tempfile

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


PRE_05_VAULT = """
contract Bank {
    mapping(address => uint) balances;
    function CashOut(uint _am) {
        if (_am <= balances[msg.sender]) {
            if (msg.sender.call.value(_am)()) {
                balances[msg.sender] -= _am;
            }
        }
    }
}
"""


def test_pre_05_idioms_reach_quorum():
    """Before 0.5 the call was `.call.value(x)()` and a function with no visibility keyword was
    public. 29 of the 32 reentrancy files in SmartBugs-curated use both; the first benchmark run
    scored 0% on them because neither lens could see the call."""
    from quorum.agents import callorder_lens, guard_lens

    seen = {s.lens for s in callorder_lens("Bank.sol", PRE_05_VAULT) + guard_lens("Bank.sol", PRE_05_VAULT)
            if s.function == "CashOut" and s.risk == "reentrancy"}
    assert seen == {"callorder-lens", "guard-lens"}


PRE_05_FALLBACK = """pragma solidity ^0.4.19;
contract Jar {
    mapping(address => uint) public balances;
    function () payable {
        if (!msg.sender.call.value(balances[msg.sender])()) revert();
        balances[msg.sender] = 0;
    }
}
"""

ALIASED_VAULT = """pragma solidity ^0.4.24;
contract Bank {
    struct Acc { uint balance; }
    mapping(address => Acc) public Accounts;
    function CashOut(uint amount) public {
        var acc = Accounts[msg.sender];
        if (!msg.sender.call.value(amount)()) revert();
        acc.balance -= amount;
    }
}
"""


def _reentrancy_lenses_on(src: str, function: str) -> set[str]:
    from quorum.agents import callorder_lens, guard_lens

    return {s.lens for s in callorder_lens("X.sol", src) + guard_lens("X.sol", src)
            if s.function == function and s.risk == "reentrancy"}


def test_unnamed_fallback_is_a_function():
    """A 0.4 fallback has no name. Before this the parser skipped it, so a labelled bug inside one
    was silently dropped from the benchmark's targets, which flattered recall."""
    from quorum.agents import parse_functions

    assert [fn.name for fn in parse_functions(PRE_05_FALLBACK)] == ["fallback"]
    assert _reentrancy_lenses_on(PRE_05_FALLBACK, "fallback") == {"callorder-lens", "guard-lens"}


def test_callorder_lens_follows_a_storage_alias():
    """`var acc = Accounts[msg.sender]; acc.balance -= x` writes storage through a local name.
    The largest remaining reentrancy miss on SmartBugs-curated was this shape."""
    assert _reentrancy_lenses_on(ALIASED_VAULT, "CashOut") == {"callorder-lens", "guard-lens"}
