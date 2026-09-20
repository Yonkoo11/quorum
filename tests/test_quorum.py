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


def test_sarif_names_both_witnesses_and_no_candidates(tmp_path):
    """A SARIF result is the product's claim in the buyer's tool: both lenses, what each read,
    the idiom signature as the fingerprint. Candidates are not findings and are not written."""
    import json
    import subprocess
    import sys

    out = tmp_path / "q.sarif"
    fixtures = ["fixtures/VulnerableVault.sol", "fixtures/OpenFeeSetter.sol"]
    subprocess.run([sys.executable, "-m", "quorum.cli", "--db", _db(), "run", "--targets", *fixtures,
                    "--sarif", str(out)], check=True, capture_output=True)
    log = json.loads(out.read_text())
    results = log["runs"][0]["results"]
    assert len(results) == 3, "confirmed 2, recalled 1 on the fixtures; the five candidates are left out"
    assert {r["ruleId"] for r in results} == {"reentrancy", "unguarded-state-write"}
    quorum = [r for r in results if r["properties"]["confirmedVia"] == "quorum"]
    recalled = [r for r in results if r["properties"]["confirmedVia"] == "recall"]
    assert len(quorum) == 2 and len(recalled) == 1
    for r in quorum:
        assert len(r["properties"]["seenBy"]) == 2
        for lens in r["properties"]["seenBy"]:
            assert lens in r["message"]["text"]
    assert "Recognised from memory" in recalled[0]["message"]["text"]
    for r in results:
        assert r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] in fixtures
        assert r["partialFingerprints"]["quorum/idiom/v1"].startswith(r["ruleId"] + ":")


OLD_COUNTER = """pragma solidity ^0.4.24;
contract Counter {
    uint256 public count = 1;
    function run(uint256 input) public {
        count += input;
    }
    function safe(uint256 input) public {
        require(input < 1000);
        count += input;
    }
}
"""

CHECKED_COUNTER = OLD_COUNTER.replace("^0.4.24", "^0.8.20")


def _math_lenses_on(src: str, function: str) -> set[str]:
    from quorum.agents import bound_lens, wrap_lens

    return {s.lens for s in wrap_lens("C.sol", src) + bound_lens("C.sol", src)
            if s.function == function and s.risk == "unsafe-math"}


def test_arithmetic_pair_reads_one_bug_from_two_sides():
    """wrap-lens reads the compiler (can it wrap?), bound-lens reads the code (is it bounded?).
    Both fire only on the same storage arithmetic, so they can actually agree, which the old
    pair (unchecked blocks vs divide-before-multiply) never could."""
    assert _math_lenses_on(OLD_COUNTER, "run") == {"wrap-lens", "bound-lens"}
    assert _math_lenses_on(OLD_COUNTER, "safe") == {"wrap-lens"}          # bounded: one witness only
    assert _math_lenses_on(CHECKED_COUNTER, "run") == {"bound-lens"}      # 0.8 checks it: one witness only


def test_unchecked_block_on_modern_code_is_wrapping():
    src = """pragma solidity ^0.8.20;
contract Tally {
    uint256 public total;
    function bump(uint256 by) external {
        unchecked {
            total += by;
        }
    }
}
"""
    assert _math_lenses_on(src, "bump") == {"wrap-lens", "bound-lens"}


ONE_LENS_PAYOUT = """pragma solidity ^0.8.0;
contract Payout {
    mapping(address => uint256) public owed;
    function pay() external {
        (bool ok, ) = msg.sender.call{value: owed[msg.sender]}("");
        require(ok);
    }
}
"""


def test_imported_pattern_never_confirms_alone_and_is_upgraded_by_local_quorum():
    """Before this, an imported pattern was recalled from one sighting exactly like a pattern this
    swarm had confirmed itself, so one paid reveal could make every importing swarm publish a chosen
    shape. Now it is a hint until two local lenses agree."""
    from quorum.agents import guard_lens

    db = _db()
    m = SwarmMemory(db)
    sig = guard_lens("P.sol", ONE_LENS_PAYOUT)[0].signature
    assert m.import_pattern({"risk": "reentrancy", "signature": sig, "corroborated_by": ["a", "b"], "contract": "X.sol"},
                            "0xclaim", "0xburn") == "imported"
    r = run_swarm(SwarmMemory(db), {"P.sol": ONE_LENS_PAYOUT})
    assert r.recalled == [] and r.promoted == []
    assert r.candidates and r.candidates[0].get("hint", {}).get("claim_tx") == "0xclaim"

    # local quorum on the same idiom (call then write, no guard) upgrades the pattern to local trust
    run_swarm(SwarmMemory(db), {"V.sol": VULN})
    assert m.trust_of(m.known_pattern(signature("reentrancy", '(bool success, ) = msg.sender.call{value: amount}("");'))) == "local"


def test_signature_v2_keeps_the_member_name():
    """v1 collapsed every identifier, so a delegatecall and an approve hashed the same and one
    retirement silenced both. The receiver and arguments still collapse; the member does not."""
    same = signature("reentrancy", '(bool ok, ) = msg.sender.call{value: amt}("");') == \
           signature("reentrancy", '(bool success1, ) = feeDest.call{value: fee}("");')
    assert same
    assert signature("r", "target.delegatecall(payload);") != signature("r", "token.approve(spender);")
    assert signature("r", "to.transfer(amount);") != signature("r", "logger.record(nonce);")
    assert signature("r", '(bool ok, ) = msg.sender.call{value: amount}("");') != \
           signature("r", '(bool ok, ) = weth.deposit{value: amount}("");')


def test_second_run_on_the_same_memory_keeps_the_findings_in_sarif(tmp_path):
    """A finding confirmed yesterday is still a finding today. Dropping it from the log would
    make the Security tab close the alert as fixed."""
    from quorum import sarif

    db = _db()
    first = run_swarm(SwarmMemory(db), {"V.sol": VULN})
    second = run_swarm(SwarmMemory(db), {"V.sol": VULN}, fresh_claims=True)
    assert second.promoted == [] and second.standing
    n1 = len(sarif.to_sarif(first, {})["runs"][0]["results"])
    n2 = len(sarif.to_sarif(second, {})["runs"][0]["results"])
    assert n1 == n2 == 1


def test_sarif_message_cannot_carry_a_link_and_is_bounded():
    from quorum import sarif

    planted = 'x.call{value: 1}("") // [view report](https://evil.example) ' + "a" * 500
    f = {"risk": "reentrancy", "contract": "C.sol", "function": "f", "lens": "guard-lens", "line": 3,
         "evidence": planted, "signature": "reentrancy:0000000000000000", "seen_by": ["guard-lens"]}
    text = sarif._message(f)
    assert "[view report](" not in text and "\\[view report\\]" in text
    assert len(text) < 700


def test_stipend_transfer_is_not_an_external_call_but_a_token_transfer_is():
    """`addr.transfer(x)` forwards 2300 gas and cannot re-enter. `token.transfer(to, amt)` can:
    an ERC777 hook runs inside it (DeFiVulnLabs ERC777-reentrancy.sol:claim)."""
    src = """pragma solidity ^0.4.24;
contract A {
    mapping(address => uint) public balances;
    function payout() public {
        msg.sender.transfer(balances[msg.sender]);
        balances[msg.sender] = 0;
    }
    function claim(address to, uint amt) public {
        token.transfer(to, amt);
        balances[to] += amt;
    }
}
"""
    assert _reentrancy_lenses_on(src, "payout") == set()
    assert _reentrancy_lenses_on(src, "claim") == {"callorder-lens", "guard-lens"}


def test_parser_ignores_braces_in_comments_and_counts_lines_from_the_brace():
    from quorum.agents import parse_functions

    src = """pragma solidity ^0.4.24;
contract A {
    function a() public {
        // if (x) {
        y = 1;
    }
    function b(uint p,
               uint q) public {
        z = p + q;
    }
}
"""
    fns = {f.name: f for f in parse_functions(src)}
    assert set(fns) == {"a", "b"}, "the commented brace must not swallow b"
    assert fns["b"].body_line == 8 and fns["b"].contract == "A"
    from quorum.agents import _lines
    assert dict(_lines(fns["b"]))[9].startswith("z = p + q")


def test_old_constructor_and_constant_function_are_not_unguarded_writes():
    from quorum.agents import modifier_lens, sender_lens

    src = """pragma solidity ^0.4.24;
contract Sale {
    address public owner;
    uint public price;
    function Sale(address _owner) public { owner = _owner; }
    function quote() public constant returns (uint) { return price * 2; }
    function setPrice(uint p) public { price = p; }
}
"""
    hits = {s.function for s in modifier_lens("S.sol", src) + sender_lens("S.sol", src)}
    assert hits == {"setPrice"}


def test_bound_lens_reads_dotted_chain_values_and_equality_bounds():
    src = """pragma solidity ^0.4.24;
contract T {
    uint public total;
    uint public lockTime;
    uint public sellerBalance;
    function a() public payable { total += msg.value; }
    function b() public { lockTime = now + 1 weeks; }
    function c(uint value) public { sellerBalance += value; }
    function d(uint n) public payable {
        require(msg.value == n);
        total += n;
    }
}
"""
    assert _math_lenses_on(src, "a") == {"wrap-lens"}
    assert _math_lenses_on(src, "b") == {"wrap-lens"}
    assert _math_lenses_on(src, "c") == {"wrap-lens", "bound-lens"}, "a parameter named `value` is not msg.value"
    assert _math_lenses_on(src, "d") == {"wrap-lens"}, "an equality check bounds n"


ONE_WAY_VAULT = '''pragma solidity ^0.8.20;
contract Rewards {
    mapping(address => uint256) public credits;
    mapping(address => uint256) public stake;
    uint256 public totalDeposited;
    address public owner;
    uint256 public feeRate;
    function deposit() external payable {
        credits[msg.sender] += msg.value;
        totalDeposited += msg.value;
    }
    function claim(uint256 amount) external {
        require(credits[msg.sender] >= amount, "no credit");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);
    }
    function unstake(uint256 amount) external {
        require(stake[msg.sender] >= amount, "no stake");
        payable(msg.sender).transfer(amount);
    }
    function slash(address who) external {
        require(msg.sender == owner);
        stake[who] = 0;
    }
    function setCap(uint256 cap) external {
        require(cap >= totalDeposited, "below deposits");
        feeRate = cap;
    }
    function sweep() external {
        require(msg.sender == owner);
        payable(owner).transfer(address(this).balance / feeRate);
    }
}
'''
FIXED_VAULT = ONE_WAY_VAULT.replace('require(credits[msg.sender] >= amount, "no credit");',
                                    'require(credits[msg.sender] >= amount, "no credit");\n        credits[msg.sender] -= amount;')


def _accounting_lenses_on(src: str, function: str) -> set[str]:
    from quorum.agents import ledger_lens, payout_lens

    return {s.lens for s in ledger_lens("R.sol", src) + payout_lens("R.sol", src)
            if s.function == function and s.risk == "accounting-mismatch"}


def test_accounting_pair_reads_one_bug_from_two_sides():
    """ledger-lens reads the contract (does this balance ever go down?), payout-lens reads the function
    (does value leave against a balance it never reduces?). The announced shape: a contract that adds
    to a balance in one function and never takes it back in another."""
    assert _accounting_lenses_on(ONE_WAY_VAULT, "claim") == {"ledger-lens", "payout-lens"}
    assert _accounting_lenses_on(FIXED_VAULT, "claim") == set()                 # the twin takes it back
    assert _accounting_lenses_on(ONE_WAY_VAULT, "setCap") == {"ledger-lens"}    # a counter that only grows, no payout
    assert _accounting_lenses_on(ONE_WAY_VAULT, "unstake") == {"payout-lens"}   # slash() lowers stake elsewhere: one witness
    assert _accounting_lenses_on(ONE_WAY_VAULT, "sweep") == set()               # owner and feeRate are configuration, not balances
    assert _accounting_lenses_on(ONE_WAY_VAULT, "deposit") == set()             # the crediting function writes the ledger


def test_accounting_pair_confirms_only_together():
    m = SwarmMemory(_db())
    r = run_swarm(m, {"R.sol": ONE_WAY_VAULT})
    # setCap also reaches quorum on the access pair (an open setter of feeRate), which is the swarm being right about the fixture
    keys = {f"{f['contract']}:{f['function']}:{f['risk']}" for f in r.promoted if f["risk"] == "accounting-mismatch"}
    assert keys == {"R.sol:claim:accounting-mismatch"}
    held = {f"{c['contract']}:{c['function']}:{c['risk']}" for c in r.candidates}
    assert "R.sol:setCap:accounting-mismatch" in held and "R.sol:unstake:accounting-mismatch" in held
    assert run_swarm(NoMemory(_db()), {"R.sol": ONE_WAY_VAULT}).promoted == []
    fixed = run_swarm(SwarmMemory(_db()), {"R.sol": FIXED_VAULT}).promoted
    assert not [f for f in fixed if f["risk"] == "accounting-mismatch"]


# ---- after the Robinhood Chain run (bench/ROBINHOOD.md): five changes, each with the shape that taught it ----

HELPER_VAULT = """
pragma solidity ^0.8.24;
contract Vault {
    mapping(address => uint256) public balanceOf;
    mapping(address => uint256) public rewardDebt;
    uint256 public accRewardPerShare;
    function claim() external returns (uint256 amount) { amount = _claim(msg.sender); }
    function _claim(address user) private returns (uint256 amount) {
        uint256 accumulated = balanceOf[user] * accRewardPerShare;
        amount = accumulated - rewardDebt[user];
        (bool ok, ) = payable(user).call{value: amount}("");
        require(ok);
        rewardDebt[user] = accumulated;
    }
}
"""

OWNER_PAYS = """
pragma solidity ^0.8.24;
contract Treasury {
    address public owner;
    uint256 public paid;
    modifier onlyOwner() { require(msg.sender == owner); _; }
    function pay(address to, uint256 amount) external onlyOwner {
        (bool ok, ) = to.call{value: amount}("");
        require(ok);
        paid += amount;
    }
}
"""

ALIAS_LEDGER = """
pragma solidity ^0.8.24;
contract Staking {
    struct Info { uint256 amount; }
    mapping(address => Info) public users;
    function stake(uint256 amount) external { users[msg.sender].amount += amount; }
    function unstake(uint256 amount) external {
        Info storage u = users[msg.sender];
        u.amount -= amount;
        payable(msg.sender).transfer(amount);
    }
}
"""

ONE_LINE_DEBIT = """
pragma solidity ^0.8.24;
contract Pool {
    mapping(address => uint256) public staked;
    function stake() external payable { staked[msg.sender] += msg.value; }
    function unstake(uint256 amount) external {
        unchecked { staked[msg.sender] -= amount; }
        payable(msg.sender).transfer(amount);
    }
}
"""

SPLIT_SUM = """
pragma solidity ^0.8.20;
contract Token {
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    function mint(address to, uint256 amount) external {
        totalSupply += amount;
        unchecked { balanceOf[to] += amount; }
    }
}
"""


def _reentrancy_lenses_on(src: str, function: str) -> set[str]:
    from quorum.agents import callorder_lens, guard_lens

    return {s.lens for s in callorder_lens("C.sol", src) + guard_lens("C.sol", src)
            if s.function == function and s.risk == "reentrancy"}


def test_reentrancy_seen_through_a_private_helper():
    """The Sherwood vault shape: the paying line lives in a private function three external ones call."""
    assert _reentrancy_lenses_on(HELPER_VAULT, "claim") == {"callorder-lens", "guard-lens"}
    assert _reentrancy_lenses_on(HELPER_VAULT, "_claim") == set()  # the helper is not an entry point


def test_owner_only_function_is_not_a_reentrancy_target():
    assert _reentrancy_lenses_on(OWNER_PAYS, "pay") == set()


def test_ledger_reduced_through_a_storage_alias_is_two_way():
    from quorum.agents import one_way_ledgers

    assert one_way_ledgers(ALIAS_LEDGER) == set()
    assert _accounting_lenses_on(ALIAS_LEDGER, "unstake") == set()


def test_ledger_reduced_on_a_one_line_block_is_two_way():
    from quorum.agents import one_way_ledgers

    assert one_way_ledgers(ONE_LINE_DEBIT) == set()


def test_unsafe_math_needs_both_readings_of_the_same_sum():
    """wrap-lens on the unchecked add, bound-lens on the checked add above it: two candidates, no finding."""
    assert _math_lenses_on(SPLIT_SUM, "mint") == {"wrap-lens", "bound-lens"}
    with tempfile.TemporaryDirectory() as d:
        report = run_swarm(SwarmMemory(os.path.join(d, "m.db")), {"Token.sol": SPLIT_SUM})
    assert not [f for f in report.promoted if f["risk"] == "unsafe-math"]
    assert [c for c in report.candidates if c["risk"] == "unsafe-math"]


def test_member_only_function_is_still_a_reentrancy_target():
    src = OWNER_PAYS.replace("onlyOwner", "onlyMember")
    assert _reentrancy_lenses_on(src, "pay") == {"callorder-lens", "guard-lens"}


def test_summary_page_names_both_witnesses_and_counts_candidates():
    from quorum.summary import MARK, markdown

    vuln = open("fixtures/VulnerableVault.sol").read()
    with tempfile.TemporaryDirectory() as d:
        report = run_swarm(SwarmMemory(os.path.join(d, "m.db")), {"VulnerableVault.sol": vuln})
    page = markdown(report, {"VulnerableVault.sol": "fixtures/VulnerableVault.sol"})
    assert page.startswith(MARK)
    assert "1 finding(s) confirmed" in page and "reentrancy" in page and "fixtures/VulnerableVault.sol" in page
    assert "callorder-lens, line" in page and "guard-lens, line" in page
    assert f"{len(report.candidates)} candidate(s)" in page
    quiet = markdown(run_swarm(SwarmMemory(os.path.join(d, "n.db")), {"Empty.sol": "pragma solidity ^0.8.0; contract E {}"}), {})
    assert "Nothing confirmed" in quiet


RETURNING_SETTER = """
pragma solidity ^0.8.20;
contract Factory {
    address public last;
    function create(address pool) external returns (address) {
        last = pool;
        return last;
    }
    function createGuarded(address pool) external onlyOwner returns (address) {
        last = pool;
        return last;
    }
}
"""

WRITES_IN_A_HELPER = """
pragma solidity ^0.8.20;
contract Registry {
    mapping(uint256 => address) public validators;
    uint256 public feeRate;
    function addValidator(uint256 id, address v) public {
        _add(id, v);
    }
    function _add(uint256 id, address v) internal {
        validators[id] = v;
        feeRate = 1;
    }
}
"""


def _access_lenses_on(src: str, function: str) -> set[str]:
    from quorum.agents import modifier_lens, sender_lens

    return {s.lens for s in modifier_lens("C.sol", src) + sender_lens("C.sol", src)
            if s.function == function and s.risk == "unguarded-state-write"}


def test_a_return_clause_is_not_a_modifier():
    """`external returns (address)` read as a guard hid every returning function (bench/MODERN.md)."""
    assert "modifier-lens" in _access_lenses_on(RETURNING_SETTER, "create")
    assert _access_lenses_on(RETURNING_SETTER, "createGuarded") == set()


def test_access_pair_sees_a_write_made_by_a_helper():
    assert _access_lenses_on(WRITES_IN_A_HELPER, "addValidator") == {"modifier-lens", "sender-lens"}


PAIR_WITH_LOCK = """
pragma solidity 0.8.13;
contract Pair {
    uint internal _unlocked = 1;
    mapping(address => uint) public balanceOf;
    modifier lock() {
        require(_unlocked == 1, "LOCKED");
        _unlocked = 2;
        _;
        _unlocked = 1;
    }
    function swap(address to, uint amount) external lock {
        (bool ok, ) = to.call{value: amount}("");
        require(ok);
        balanceOf[to] -= amount;
    }
    function drain(address to, uint amount) external {
        (bool ok, ) = to.call{value: amount}("");
        require(ok);
        balanceOf[to] -= amount;
    }
}
"""


def test_a_lock_modifier_is_a_reentrancy_guard():
    """`modifier lock()` over an `_unlocked` flag is the Uniswap V2 Pair idiom (bench/MODERN.md)."""
    assert _reentrancy_lenses_on(PAIR_WITH_LOCK, "swap") == {"callorder-lens"}
    assert _reentrancy_lenses_on(PAIR_WITH_LOCK, "drain") == {"callorder-lens", "guard-lens"}


# ---- reading across files: what a contract inherits (bench/MODERN.md named this as the next thing) ----

BASE_REGISTRY = """
pragma solidity ^0.8.20;
contract ValidatorRegistry {
    mapping(uint256 => mapping(address => bool)) private _validatorsMap;
    function _addValidator(uint256 id, address v) internal {
        _validatorsMap[id][v] = true;
    }
}
"""

CHILD_REGISTRY = """
pragma solidity ^0.8.20;
import {ValidatorRegistry} from "./ValidatorRegistry.sol";
contract AgentNft is ValidatorRegistry {
    function addValidator(uint256 id, address v) public {
        _addValidator(id, v);
    }
}
"""

BASE_VAULT = """
pragma solidity ^0.8.20;
contract VaultBase {
    mapping(address => uint256) public staked;
    function _debit(address a, uint256 amount) internal { staked[a] -= amount; }
}
"""

CHILD_VAULT = """
pragma solidity ^0.8.20;
import {VaultBase} from "./VaultBase.sol";
contract Vault is VaultBase {
    function stake() external payable { staked[msg.sender] += msg.value; }
    function unstake(uint256 amount) external {
        _debit(msg.sender, amount);
        payable(msg.sender).transfer(amount);
    }
}
"""


def test_a_nested_mapping_is_state():
    """`mapping(a => mapping(b => c))` stopped the declaration reader at the first bracket, so a balance
    keyed by two things was not state at all (bench/MODERN.md)."""
    from quorum.agents import state_vars

    assert "_validatorsMap" in state_vars(BASE_REGISTRY)


def test_the_project_resolves_what_a_contract_inherits():
    from quorum.agents import Project

    p = Project.read({"ValidatorRegistry.sol": BASE_REGISTRY, "AgentNft.sol": CHILD_REGISTRY})
    assert p.parents["AgentNft"] == ["ValidatorRegistry"]
    assert "_validatorsMap" in p.vars_of("AgentNft")
    assert "_addValidator" in p.helpers_of("AgentNft")
    assert p.vars_of("ValidatorRegistry") == set()   # a base inherits nothing here


def test_a_write_made_by_an_inherited_helper_is_seen():
    from quorum.agents import Project, modifier_lens

    p = Project.read({"ValidatorRegistry.sol": BASE_REGISTRY, "AgentNft.sol": CHILD_REGISTRY})
    seen = {s.function for s in modifier_lens("AgentNft.sol", CHILD_REGISTRY, p)}
    assert "addValidator" in seen
    assert not modifier_lens("AgentNft.sol", CHILD_REGISTRY)  # one file alone still sees nothing


def test_an_inherited_balance_is_read_and_its_inherited_debit_is_read_with_it():
    """The child pays out against a balance declared in its base. Reading one file, the balance is not
    state at all and the payout is invisible; reading what the contract inherits, both the balance and
    the debit that keeps it honest come into view, so the pair stays quiet."""
    from quorum.agents import Project, one_way_ledgers, payout_lens

    p = Project.read({"VaultBase.sol": BASE_VAULT, "Vault.sol": CHILD_VAULT})
    assert "staked" in p.vars_of("Vault")
    assert one_way_ledgers(CHILD_VAULT, p, "Vault") == set()   # the base debits it, so it is not one-way
    assert not payout_lens("Vault.sol", CHILD_VAULT, p)
    with tempfile.TemporaryDirectory() as d:
        report = run_swarm(SwarmMemory(os.path.join(d, "m.db")),
                           {"VaultBase.sol": BASE_VAULT, "Vault.sol": CHILD_VAULT})
    assert not [f for f in report.promoted if f["risk"] == "accounting-mismatch"]


CONSISTENT_REGISTRY = """
pragma solidity ^0.8.20;

interface IConfig { function admin() external view returns (address); }

contract Registry {
    mapping(address => bool) public members;
    mapping(address => uint256) public quota;
    address public admin;
    address public config;

    modifier onlyAdmin() { require(msg.sender == admin, "not admin"); _; }

    function addMember(address who) external onlyAdmin { members[who] = true; }

    function dropMember(address who) external onlyAdmin { members[who] = false; }

    function joinMember(address who) external { members[who] = true; }

    function releaseQuota(address who) external {
        require(msg.sender == who, "not you");
        quota[who] = 0;
    }

    function claimSeat(address who) external initializer { members[who] = true; }

    function setQuotaFor(address who, uint256 amount) external onlyAdmin { quota[who] = amount; }

    function setQuota(uint256 amount) external { quota[msg.sender] = amount; }

    function setAdmin(address who) external onlyAdmin { admin = who; }

    function refreshAdmin() external { admin = IConfig(config).admin(); }
}
"""


def _consistency(src):
    from quorum.agents import consistency_lens

    return {s.function for s in consistency_lens("Registry.sol", src)}


def test_the_contract_says_what_the_guard_for_a_variable_is():
    """Two functions write `members` behind onlyAdmin and one writes it behind nothing. The variable is
    named nothing like a fee or an owner, so the older reading of this risk cannot see it; the
    disagreement between siblings is the evidence."""
    assert "joinMember" in _consistency(CONSISTENT_REGISTRY)


def test_the_siblings_that_agree_are_not_themselves_sighted():
    seen = _consistency(CONSISTENT_REGISTRY)
    assert "addMember" not in seen and "dropMember" not in seen and "setQuotaFor" not in seen


def test_a_function_that_tests_its_own_caller_is_not_missing_the_guard():
    """`releaseQuota` carries no modifier at all, and is nobody's access-control gap: it decides for
    itself who may call it. Five of the hand-read false confirmations in bench/MODERN.md were this."""
    assert "releaseQuota" not in _consistency(CONSISTENT_REGISTRY)


def test_a_one_shot_initializer_is_guarded_by_being_one_shot():
    """After deployment nobody can call it, so what its siblings carry says nothing about it. Ten of
    the confirmations on the modern corpus were an initializer beside a guarded setter."""
    assert "claimSeat" not in _consistency(CONSISTENT_REGISTRY)


def test_a_caller_writing_only_their_own_slot_is_not_the_shape():
    """`quota[msg.sender]` is the caller's own row. `setQuotaFor` writes any row and is guarded; that
    difference is the design, not a disagreement."""
    assert "setQuota" not in _consistency(CONSISTENT_REGISTRY)


def test_a_write_the_caller_cannot_reach_is_not_the_shape():
    """`refreshAdmin` copies a value out of a contract the protocol chose, into a slot the caller does
    not pick. Taking no permission to call it costs an attacker nothing, because they decide nothing."""
    assert "refreshAdmin" not in _consistency(CONSISTENT_REGISTRY)


READS_TWO = """
pragma solidity ^0.4.19;

contract Fund {
    mapping(address => uint256) balances;
    uint256 MinDeposit;

    function CashOut(uint256 amount) public {
        if (balances[msg.sender] >= MinDeposit) {
            balances[msg.sender] -= amount;
            msg.sender.transfer(amount);
        }
    }
}
"""


def test_a_line_that_mentions_two_balances_reports_both():
    """It reported only the first, taken from a set, and Python randomises set order per process. The
    same file then confirmed an accounting finding on one run and not on the next, on identical code:
    payout-lens intersects what a function reads with what it writes, and which name it saw was luck."""
    from quorum.agents import _reads, parse_functions

    fn = next(f for f in parse_functions(READS_TWO) if f.name == "CashOut")
    seen = [v for _, _, v in _reads(fn, {"balances", "MinDeposit"})]
    guard_line = [v for ln, text, v in _reads(fn, {"balances", "MinDeposit"}) if ">= MinDeposit" in text]
    assert guard_line == ["MinDeposit", "balances"]      # every match on the line, in a fixed order
    assert seen == sorted(seen, key=lambda v: (seen.index(v), v)) and set(seen) == {"MinDeposit", "balances"}


def test_the_payout_reading_sees_the_debit_beside_the_check():
    """With both names in hand, a function that lowers the balance it checks is not a one-way payout."""
    from quorum.agents import payout_lens

    assert not payout_lens("Fund.sol", READS_TWO)
