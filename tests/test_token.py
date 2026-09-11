"""The token touches exactly one thing: publishing to the shared registry.

These tests never reach a chain. They pin the calldata shapes, the digest
check a reveal must pass, the burn rules a claim must satisfy, and that a
pattern nobody paid to publish never enters memory.
"""

import os
import tempfile
from unittest import mock

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
