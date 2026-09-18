"""The token touches exactly one thing: publishing to the shared registry.

These tests never reach a chain. They pin the calldata shapes, the digest
check a reveal must pass, the burn rules a claim must satisfy, and that a
pattern nobody paid to publish never enters memory.
"""

import os
import tempfile
from unittest import mock

import pytest

from web3.exceptions import TransactionNotFound

from quorum import chain
from quorum.memory import NoMemory, SwarmMemory

FINDING = {
    "risk": "reentrancy",
    "signature": "reentrancy:97d18d17cfa4494a",
    "contract": "VulnerableVault.sol",
    "function": "withdraw",
    "seen_by": ["guard-lens", "callorder-lens"],
}
DIGEST = chain.claim_digest(FINDING)
BURN_TX = bytes.fromhex("ab" * 32)


def _db():
    return os.path.join(tempfile.mkdtemp(), "m.db")


def test_v2_claim_round_trips_and_v1_still_reads():
    data = chain.encode_claim(DIGEST, BURN_TX)
    parsed = chain.decode_claim(data)
    assert parsed == {"version": 2, "digest": "0x" + DIGEST.hex(), "burn_tx": "0x" + BURN_TX.hex()}
    legacy = chain.decode_claim(chain.PREFIX + DIGEST)
    assert legacy["version"] == 1 and legacy["burn_tx"] is None and legacy["digest"] == "0x" + DIGEST.hex()


def test_reveal_fields_hash_to_the_claim_digest():
    fields = chain.reveal_fields(FINDING)
    data = chain.encode_reveal(bytes.fromhex("cd" * 32), fields)
    parsed = chain.decode_reveal(data)
    recomputed = chain.claim_digest({**parsed["fields"], "seen_by": parsed["fields"]["corroborated_by"]})
    assert recomputed == DIGEST
    tampered = {**parsed["fields"], "risk": "unsafe-math"}
    assert chain.claim_digest({**tampered, "seen_by": tampered["corroborated_by"]}) != DIGEST


def _fake_burn_tx(to, amount, status=1, block=chain.FEE_RAISE_BLOCK + 1):
    data = chain.BURN_SELECTOR + amount.to_bytes(32, "big")
    tx = {"to": to, "input": data, "from": "0xf9946775891a24462cD4ec885d0D4E2675C84355"}
    receipt = {"blockNumber": block, "status": status}
    w3 = mock.Mock()
    w3.eth.get_transaction.return_value = tx
    w3.eth.get_transaction_receipt.return_value = receipt
    return w3


def test_burn_is_valid_only_for_the_fee_on_the_token():
    with mock.patch.object(chain, "_token_w3", return_value=_fake_burn_tx(chain.TOKEN, chain.CLAIM_FEE)):
        assert chain.read_burn("0x" + "01" * 32)["valid"]
    with mock.patch.object(chain, "_token_w3", return_value=_fake_burn_tx(chain.TOKEN, chain.CLAIM_FEE - 1)):
        assert not chain.read_burn("0x" + "01" * 32)["valid"]
    with mock.patch.object(chain, "_token_w3", return_value=_fake_burn_tx(chain.TOKEN, chain.CLAIM_FEE, status=0)):
        assert not chain.read_burn("0x" + "01" * 32)["valid"]
    other = "0x" + "11" * 20
    with mock.patch.object(chain, "_token_w3", return_value=_fake_burn_tx(other, chain.CLAIM_FEE)):
        assert not chain.read_burn("0x" + "01" * 32)["valid"]


def test_import_learns_a_paid_pattern_once_and_no_memory_never():
    m = SwarmMemory(_db())
    fields = chain.reveal_fields(FINDING)
    assert m.import_pattern(fields, "0xclaim", "0xburn")
    assert m.known_pattern(FINDING["signature"])["imported_from"]["fee_burn_tx"] == "0xburn"
    assert m.import_pattern(fields, "0xclaim", "0xburn") == "known"
    assert not NoMemory(_db()).import_pattern(fields, "0xclaim", "0xburn")


def test_scanner_has_no_token_dependency():
    """The promise on the account: scanning never touches the token."""
    import inspect
    from quorum import agents, swarm, memory
    for mod in (agents, swarm, memory):
        src = inspect.getsource(mod)
        assert "import chain" not in src and "chain." not in src
        assert "CLAIM_FEE" not in src and "burn(" not in src


def test_claims_and_fee_share_one_chain_by_default():
    """The token is on Robinhood Chain, so the claim goes there too: one RPC to verify both halves."""
    assert chain.CHAIN_ID == chain.TOKEN_CHAIN_ID == 4663
    assert chain.chain_name() == "Robinhood Chain"
    assert chain.EXPLORER == chain.TOKEN_EXPLORER
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("QUORUM_RPC", None); os.environ.pop("QUORUM_TOKEN_RPC", None)
        assert chain._rpc(4663) == "https://rpc.mainnet.chain.robinhood.com"
    with mock.patch.dict(os.environ, {"QUORUM_RPC": "http://node"}):
        assert chain._rpc(4663) == "http://node"


def _fake_chain(chain_id, tx=None, calldata=None):
    w3 = mock.Mock()
    w3.eth.chain_id = chain_id
    if tx is None:
        w3.eth.get_transaction.side_effect = TransactionNotFound("not here")
    else:
        w3.eth.get_transaction.return_value = {"from": tx, "input": calldata}
        w3.eth.get_transaction_receipt.return_value = {"blockNumber": 51138878, "status": 1}
        w3.eth.get_block.return_value = {"timestamp": 1_757_530_000}
    return w3


def test_first_claim_on_base_still_reads_after_the_move():
    signer = "0xf9946775891a24462cD4ec885d0D4E2675C84355"
    chains = {4663: _fake_chain(4663), 8453: _fake_chain(8453, signer, chain.PREFIX + DIGEST)}
    with mock.patch.object(chain, "_w3", side_effect=lambda cid=None: chains[cid or chain.CHAIN_ID]):
        claim = chain.read_claim("0x" + "a6" * 32)
    assert claim["chain"] == "Base" and claim["chain_id"] == 8453
    assert claim["version"] == 1 and claim["burn_tx"] is None
    assert chains[4663].eth.get_transaction.called, "the claim chain is asked first"


def test_a_missing_claim_is_reported_not_invented():
    chains = {4663: _fake_chain(4663), 8453: _fake_chain(8453)}
    with mock.patch.object(chain, "_w3", side_effect=lambda cid=None: chains[cid or chain.CHAIN_ID]):
        try:
            chain.read_claim("0x" + "00" * 32)
            assert False, "should have raised"
        except RuntimeError as exc:
            assert "Robinhood Chain" in str(exc) and "Base" in str(exc)


SIGNER = "0x" + "22" * 20


REGISTRY = "0x" + "77" * 20
FEE_BYTES = chain.CLAIM_FEE.to_bytes(32, "big")


def _registry_tx(signer=SIGNER, claimant=SIGNER, digest=DIGEST, registry=REGISTRY, chain_id=chain.TOKEN_CHAIN_ID,
                 status=1, logs=None, timestamp=1_757_700_000):
    """A transaction to the registry whose receipt carries the Claimed log (or whatever logs are given)."""
    if logs is None:
        logs = [{"address": registry, "topics": [chain.CLAIMED_TOPIC, digest, bytes(12) + bytes.fromhex(claimant[2:])],
                 "data": FEE_BYTES}]
    w3 = mock.Mock()
    w3.eth.chain_id = chain_id
    w3.eth.get_transaction.return_value = {"from": signer, "to": registry, "input": b"\x12\x34\x56\x78" + digest}
    w3.eth.get_transaction_receipt.return_value = {"blockNumber": 62_400_000, "status": status, "logs": logs}
    w3.eth.get_block.return_value = {"timestamp": timestamp}
    return w3


def _on_registry_chain(w3):
    return mock.patch.multiple(chain, REGISTRY=REGISTRY, REGISTRY_SINCE=1_757_650_000, CHAIN_ID=chain.TOKEN_CHAIN_ID,
                               _w3=mock.Mock(side_effect=lambda cid=None: w3))


def test_registry_claim_reads_from_the_log_and_stands():
    with _on_registry_chain(_registry_tx()):
        claim = chain.read_claim("0x" + "01" * 32)
    assert claim["version"] == 3 and claim["registry"] == REGISTRY and claim["burn_tx"] is None
    assert claim["from"] == SIGNER and claim["digest"] == "0x" + DIGEST.hex() and claim["fee"] == chain.CLAIM_FEE
    assert chain.claim_problem(claim) is None
    assert "reverted" in chain.claim_problem({**claim, "status": 0})


def test_a_claimed_log_from_another_address_is_not_a_claim():
    with _on_registry_chain(_registry_tx(registry="0x" + "66" * 20)):
        with pytest.raises(RuntimeError) as exc:
            chain.read_claim("0x" + "01" * 32)
    assert "not a Quorum claim" in str(exc.value)


def test_two_claimed_logs_in_one_transaction_are_refused():
    log = {"address": REGISTRY, "topics": [chain.CLAIMED_TOPIC, DIGEST, bytes(12) + bytes.fromhex(SIGNER[2:])], "data": FEE_BYTES}
    with _on_registry_chain(_registry_tx(logs=[log, dict(log)])):
        with pytest.raises(RuntimeError) as exc:
            chain.read_claim("0x" + "01" * 32)
    assert "one claim per transaction" in str(exc.value)


def test_a_self_addressed_claim_after_the_registry_is_refused_and_one_before_stands():
    v2 = {"chain_id": 4663, "block": 60762176, "status": 1, "self_addressed": True, "burn_tx": "0x" + "ab" * 32,
          "version": 2, "timestamp": 1_757_600_000}
    with mock.patch.object(chain, "REGISTRY_SINCE", 1_757_650_000):
        assert chain.claim_problem(v2) is None
        assert "after the registry" in chain.claim_problem({**v2, "timestamp": 1_757_700_000})
    with mock.patch.object(chain, "REGISTRY_SINCE", None):
        assert chain.claim_problem({**v2, "timestamp": 1_757_700_000}) is None


def test_attest_approves_only_when_short_then_claims_through_the_registry():
    calls = []
    common = dict(REGISTRY=REGISTRY, CHAIN_ID=chain.TOKEN_CHAIN_ID, _w3=mock.Mock(), token_balance=mock.Mock(return_value=chain.CLAIM_FEE),
                  approve_fee=mock.Mock(side_effect=lambda w3, acct: calls.append("approve") or {"tx": "0xa", "url": "u", "block": 1, "status": 1}),
                  claim_via_registry=mock.Mock(side_effect=lambda w3, acct, d: calls.append("claim") or {"tx": "0xc", "block": 2, "gas_used": 1, "status": 1}))
    with mock.patch.multiple(chain, _allowance=mock.Mock(return_value=0), **common), mock.patch.object(chain, "_account") as acct:
        acct.return_value.address = SIGNER
        result = chain.attest(FINDING)
    assert calls == ["approve", "claim"] and result["registry"] == REGISTRY and result["approve"]["tx"] == "0xa"
    calls.clear()
    with mock.patch.multiple(chain, _allowance=mock.Mock(return_value=chain.CLAIM_FEE), **common), mock.patch.object(chain, "_account") as acct:
        acct.return_value.address = SIGNER
        result = chain.attest(FINDING)
    assert calls == ["claim"] and result["approve"] is None


def test_attest_refuses_without_a_registry_or_off_its_chain_or_without_the_fee():
    with mock.patch.multiple(chain, REGISTRY=None, CHAIN_ID=chain.TOKEN_CHAIN_ID), pytest.raises(RuntimeError) as exc:
        chain.attest(FINDING)
    assert "QUORUM_REGISTRY" in str(exc.value)
    with mock.patch.multiple(chain, REGISTRY=REGISTRY, CHAIN_ID=8453), pytest.raises(RuntimeError) as exc:
        chain.attest(FINDING)
    assert "unset QUORUM_CHAIN_ID" in str(exc.value)
    with mock.patch.multiple(chain, REGISTRY=REGISTRY, CHAIN_ID=chain.TOKEN_CHAIN_ID, _w3=mock.Mock(),
                             token_balance=mock.Mock(return_value=chain.CLAIM_FEE - 1), claim_via_registry=mock.Mock()) as patched, \
         mock.patch.object(chain, "_account"), pytest.raises(RuntimeError) as exc:
        chain.attest(FINDING)
    assert "burns" in str(exc.value)


def test_a_reveal_of_a_registry_claim_is_paid_by_construction_and_charged_to_the_claim():
    fields = chain.reveal_fields(FINDING)
    claim = {"chain_id": 4663, "chain": "Robinhood Chain", "from": SIGNER, "digest": "0x" + DIGEST.hex(), "burn_tx": None,
             "registry": REGISTRY, "version": 3, "status": 1, "block": 1, "timestamp": 1}
    reveal_tx = {"from": SIGNER, "input": chain.encode_reveal(bytes.fromhex("cd" * 32), fields)}
    with mock.patch.object(chain, "_find_tx", return_value=(4663, mock.Mock(), reveal_tx)), \
         mock.patch.object(chain, "read_claim", return_value=claim), mock.patch.object(chain, "read_burn") as burn:
        r = chain.read_reveal("0x" + "ef" * 32)
    burn.assert_not_called()
    assert r["fee_paid"] and r["same_signer"] and r["digest_matches"] and r["payment"] == "0x" + "cd" * 32


def test_send_returns_a_0x_prefixed_hash():
    """Explorer links and memory records must carry the canonical 0x form."""
    from hexbytes import HexBytes
    w3 = mock.Mock()
    w3.eth.get_transaction_count.return_value = 0
    w3.eth.estimate_gas.return_value = 21000
    w3.eth.fee_history.return_value = {"baseFeePerGas": [10]}
    w3.to_wei.return_value = 1
    w3.eth.send_raw_transaction.return_value = HexBytes("ab" * 32)
    w3.eth.wait_for_transaction_receipt.return_value = {"blockNumber": 1, "gasUsed": 1, "status": 1}
    acct = mock.Mock(); acct.address = SIGNER
    assert chain._send(w3, acct, {})["tx"] == "0x" + "ab" * 32


def test_fee_is_judged_at_the_burns_own_block():
    """Raising the fee must not break claims paid at the launch rate."""
    launch, raised = chain.FEE_SCHEDULE[0][1], chain.FEE_SCHEDULE[1][1]
    assert launch == 1_000 * 10**18 and raised == 100_000 * 10**18 and chain.CLAIM_FEE == raised
    assert chain.fee_at(60748823) == launch          # this morning's burn, before the raise
    assert chain.fee_at(chain.FEE_RAISE_BLOCK) == raised
    with mock.patch.object(chain, "_token_w3", return_value=_fake_burn_tx(chain.TOKEN, launch, block=60748823)):
        assert chain.read_burn("0x" + "01" * 32)["valid"]
    with mock.patch.object(chain, "_token_w3", return_value=_fake_burn_tx(chain.TOKEN, launch)):
        assert not chain.read_burn("0x" + "01" * 32)["valid"], "1,000 is not enough after the raise"
    with mock.patch.object(chain, "_token_w3", return_value=_fake_burn_tx(chain.TOKEN, raised)):
        assert chain.read_burn("0x" + "01" * 32)["valid"]


def test_import_is_a_hint_and_one_burn_admits_one_pattern():
    """A paid reveal proves someone paid. It proves nothing about the pattern, so it never confirms
    on its own, and one burn cannot seed a memory with many patterns."""
    m = SwarmMemory(_db())
    fields = chain.reveal_fields(FINDING)
    assert m.import_pattern(fields, "0xclaim", "0xburn") == "imported"
    assert m.trust_of(m.known_pattern(FINDING["signature"])) == "imported"
    assert m.import_pattern(fields, "0xclaim", "0xburn") == "known"
    other = {**fields, "signature": "reentrancy:0000000000000000"}
    assert m.import_pattern(other, "0xclaim2", "0xburn") == "burn-used"
    assert m.known_pattern(other["signature"]) is None


def test_claim_problems_reverted_unpaid_and_not_self_addressed():
    base_first = {"chain_id": 8453, "block": 51138878, "status": 1, "self_addressed": True, "burn_tx": None}
    assert chain.claim_problem(base_first) is None, "the first claim predates the fee"
    assert "unpaid" in chain.claim_problem({**base_first, "block": 51138879})
    assert "unpaid" in chain.claim_problem({**base_first, "chain_id": 4663, "block": 1})
    paid = {"chain_id": 4663, "block": 60762176, "status": 1, "self_addressed": True, "burn_tx": "0x" + "ab" * 32}
    assert chain.claim_problem(paid) is None
    assert "reverted" in chain.claim_problem({**paid, "status": 0})
    assert "self-addressed" in chain.claim_problem({**paid, "self_addressed": False})


def test_malformed_reveal_is_refused_not_crashed():
    claim_tx = bytes.fromhex("cd" * 32)
    for junk in (b"\xff\xfe", b"[1,2]", b'"text"', b'{"risk": "reentrancy"}', b'{"risk": 1, "signature": "x"}'):
        try:
            chain.decode_reveal(chain.PREFIX_REVEAL + claim_tx + junk)
            assert False, f"should have refused {junk!r}"
        except RuntimeError as exc:
            assert "not a Quorum reveal" in str(exc)
