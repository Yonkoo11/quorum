"""The token touches exactly one thing: publishing to the shared registry.

These tests never reach a chain. They pin the calldata shapes, the digest
check a reveal must pass, the burn rules a claim must satisfy, and that a
pattern nobody paid to publish never enters memory.
"""

import os
import tempfile
from unittest import mock

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


def _fake_burn_tx(to, amount, status=1):
    data = chain.BURN_SELECTOR + amount.to_bytes(32, "big")
    tx = {"to": to, "input": data, "from": "0xf9946775891a24462cD4ec885d0D4E2675C84355"}
    receipt = {"blockNumber": 1, "status": status}
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


def test_attest_burns_before_it_claims():
    calls = []
    with mock.patch.object(chain, "_w3"), mock.patch.object(chain, "_account") as acct, \
         mock.patch.object(chain, "burn_fee", side_effect=lambda: calls.append("burn") or {"tx": "0x" + "ab" * 32}), \
         mock.patch.object(chain, "_send", side_effect=lambda *a: calls.append("claim") or {"tx": "0x1", "block": 1, "gas_used": 1, "status": 1}):
        acct.return_value.address = "0x" + "22" * 20
        chain.attest(FINDING)
    assert calls == ["burn", "claim"]
    with mock.patch.object(chain, "_w3"), mock.patch.object(chain, "_account"), \
         mock.patch.object(chain, "burn_fee", side_effect=RuntimeError("no QUORUM")), \
         mock.patch.object(chain, "_send") as send:
        try:
            chain.attest(FINDING)
        except RuntimeError:
            pass
        send.assert_not_called()


def test_import_learns_a_paid_pattern_once_and_no_memory_never():
    m = SwarmMemory(_db())
    fields = chain.reveal_fields(FINDING)
    assert m.import_pattern(fields, "0xclaim", "0xburn")
    assert m.known_pattern(FINDING["signature"])["imported_from"]["fee_burn_tx"] == "0xburn"
    assert not m.import_pattern(fields, "0xclaim", "0xburn")
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


def _attest_env(burn_valid=True, burn_from=SIGNER):
    """Patches for attest with no chain: records the order of burn / record / claim."""
    calls = []
    patches = [
        mock.patch.object(chain, "_w3"),
        mock.patch.object(chain, "_account"),
        mock.patch.object(chain, "burn_fee", side_effect=lambda: calls.append("burn") or {"tx": "0x" + "ab" * 32, "url": "u"}),
        mock.patch.object(chain, "read_burn", return_value={"from": burn_from, "amount": chain.CLAIM_FEE, "block": 1, "status": 1, "valid": burn_valid}),
        mock.patch.object(chain, "_send", side_effect=lambda *a: calls.append("claim") or {"tx": "0x1", "block": 1, "gas_used": 1, "status": 1}),
    ]
    return calls, patches


def test_attest_records_the_burn_before_the_claim_is_sent():
    calls, patches = _attest_env()
    with patches[0], patches[1] as acct, patches[2], patches[3], patches[4]:
        acct.return_value.address = SIGNER
        chain.attest(FINDING, on_burn=lambda burn: calls.append("record"))
    assert calls == ["burn", "record", "claim"]


def test_attest_reuses_a_saved_burn_instead_of_burning_twice():
    calls, patches = _attest_env()
    with patches[0], patches[1] as acct, patches[2], patches[3], patches[4]:
        acct.return_value.address = SIGNER
        result = chain.attest(FINDING, burn_tx="0x" + "ab" * 32)
    assert calls == ["claim"] and result["burn"]["reused"] and result["burn"]["tx"] == "0x" + "ab" * 32


def test_attest_refuses_to_reuse_a_burn_that_is_not_the_signers_fee():
    for kwargs in ({"burn_valid": False}, {"burn_from": "0x" + "33" * 20}):
        calls, patches = _attest_env(**kwargs)
        with patches[0], patches[1] as acct, patches[2], patches[3], patches[4]:
            acct.return_value.address = SIGNER
            try:
                chain.attest(FINDING, burn_tx="0x" + "ab" * 32)
                assert False, "should have refused"
            except RuntimeError as exc:
                assert "not reusing" in str(exc)
        assert calls == []


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
