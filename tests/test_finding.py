"""Finding files: any tool's finding with a hashed proof, claimed and revealed through the same registry."""
import json
import os
import tempfile
from unittest import mock

import pytest

from quorum import chain, cli
from quorum import finding as ff

SIGNER = "0xf9946775891a24462cD4ec885d0D4E2675C84355"
REGISTRY = "0xDeA0792cEc959CE6893C24dEeFc6FE9B047a3Ea3"


def _proof(tmp_path, text="contract Exploit { function run() public {} }"):
    p = tmp_path / "exploit.t.sol"
    p.write_text(text)
    return p


def _finding(tmp_path, **over):
    f = ff.new("First depositor share inflation", "fork-exploit",
               {"chain": "Ethereum", "address": "0xAbCdEf0000000000000000000000000000000001"},
               "medium", _proof(tmp_path), program="immunefi", found_at="2026-11-07")
    return {**f, **over}


def test_digest_commits_to_kind_target_severity_and_proof_only(tmp_path):
    f = _finding(tmp_path)
    d = chain.claim_digest(f)
    assert d == ff.digest(f)
    # off-chain fields do not move the digest
    assert chain.claim_digest({**f, "title": "other", "program": "x", "status": "fixed"}) == d
    # the address is hashed lowercase: the same contract written two ways is one claim
    assert chain.claim_digest({**f, "target": {"chain": "ethereum", "address": f["target"]["address"].upper().replace("0X", "0x")}}) == d
    for change in ({"severity": "high"}, {"kind": "write-up"}, {"proof_sha256": "0" * 64},
                   {"target": {"chain": "base", "address": f["target"]["address"]}}):
        assert chain.claim_digest({**f, **change}) != d


def test_reveal_round_trips_and_a_code_target_works(tmp_path):
    f = _finding(tmp_path, target={"repo": "ZcashFoundation/zebra", "commit": "e6644c2", "path": "zebra-fuzz/fuzz/Cargo.toml"})
    fields = chain.reveal_fields(f)
    assert set(fields) == {"kind", "target", "severity", "proof_sha256"}
    data = chain.encode_reveal(bytes.fromhex("cd" * 32), fields)
    parsed = chain.decode_reveal(data)
    assert chain.claim_digest(chain.finding_from_fields(parsed["fields"])) == chain.claim_digest(f)
    # the swarm shape still decodes, and garbage still does not
    swarm = chain.encode_reveal(bytes.fromhex("cd" * 32), {"risk": "reentrancy", "signature": "s", "corroborated_by": []})
    assert chain.decode_reveal(swarm)["fields"]["risk"] == "reentrancy"
    with pytest.raises(RuntimeError, match="neither"):
        chain.decode_reveal(chain.encode_reveal(bytes.fromhex("cd" * 32), {"kind": "fork-exploit"}))


def test_load_names_the_first_thing_wrong(tmp_path):
    f = _finding(tmp_path)
    path = tmp_path / "f.json"
    for bad, msg in (({"kind": "guess"}, "kind must be"), ({"proof_sha256": "abc"}, "64 lowercase hex"),
                     ({"target": {"chain": "ethereum", "address": "0x12"}}, "40 hex"),
                     ({"target": {"repo": "zebra", "commit": "e6644c2"}}, "owner/name"), ({"quorum": 1}, '"quorum" must be 2')):
        ff.save(path, {**f, **bad})
        with pytest.raises(ValueError, match=msg):
            ff.load(path)
    (tmp_path / "x.json").write_text("{")
    with pytest.raises(ValueError, match="not a readable JSON"):
        ff.load(tmp_path / "x.json")


def test_new_hashes_the_proof_file(tmp_path):
    f = _finding(tmp_path)
    import hashlib
    assert f["proof_sha256"] == hashlib.sha256(_proof(tmp_path).read_bytes()).hexdigest()
    assert f["status"] == "committed" and f["attested_tx"] is None
    with pytest.raises(ValueError, match="proof file not found"):
        ff.new("t", "write-up", f["target"], "low", tmp_path / "missing.md")


def test_attest_from_file_writes_the_tx_back_and_skips_claimed(tmp_path, capsys):
    path = tmp_path / "f.json"
    ff.save(path, _finding(tmp_path))
    sent = {"tx": "0x" + "ab" * 32, "url": "u", "block": 1, "registry": REGISTRY, "approve": None, "digest": "00"}
    with mock.patch.object(chain, "attest", return_value=sent), mock.patch.object(chain, "token_balance", return_value=10**30), \
         mock.patch.object(chain, "address", return_value=SIGNER), mock.patch.object(chain, "balance_wei", return_value=10**18):
        assert cli.main(["attest", "--finding", str(path)]) == 0
        saved = json.loads(path.read_text())
        assert saved["attested_tx"] == sent["tx"] and saved["attested_at"]
        assert cli.main(["attest", "--finding", str(path)]) == 0
    assert "already claimed" in capsys.readouterr().out
    # a dry run writes nothing
    other = tmp_path / "g.json"
    ff.save(other, _finding(tmp_path))
    dry = {"dry_run": True, "digest": "ab" * 32, "registry": REGISTRY}
    with mock.patch.object(chain, "attest", return_value=dry), mock.patch.object(chain, "token_balance", return_value=10**30), \
         mock.patch.object(chain, "address", return_value=SIGNER), mock.patch.object(chain, "balance_wei", return_value=10**18):
        assert cli.main(["attest", "--finding", str(other), "--dry-run"]) == 0
    assert json.loads(other.read_text())["attested_tx"] is None


def test_reveal_from_file_refuses_before_the_fix_is_public(tmp_path, capsys):
    path = tmp_path / "f.json"
    ff.save(path, _finding(tmp_path, attested_tx="0x" + "ab" * 32, status="reported"))
    with mock.patch.object(chain, "reveal") as reveal:
        assert cli.main(["reveal", "--finding", str(path)]) == 1
        reveal.assert_not_called()
    assert "fix is public" in capsys.readouterr().out
    ff.save(path, _finding(tmp_path, attested_tx="0x" + "ab" * 32, status="fixed"))
    with mock.patch.object(chain, "reveal", return_value={"tx": "0x" + "cd" * 32, "url": "u"}), \
         mock.patch.object(chain, "chain_name", return_value="Robinhood Chain"):
        assert cli.main(["reveal", "--finding", str(path)]) == 0
    saved = json.loads(path.read_text())
    assert saved["revealed_tx"] == "0x" + "cd" * 32 and saved["status"] == "revealed"
    # unclaimed: refused
    ff.save(path, _finding(tmp_path, status="fixed"))
    assert cli.main(["reveal", "--finding", str(path)]) == 1


def test_public_rows_hide_the_target_until_revealed(tmp_path):
    unclaimed = _finding(tmp_path)
    claimed = _finding(tmp_path, attested_tx="0x" + "ab" * 32, attested_at="2026-11-07T00:00:00+00:00")
    revealed = {**claimed, "revealed_tx": "0x" + "cd" * 32, "status": "revealed", "public_url": "https://example.org/issue/1"}
    assert ff.public_row(unclaimed) is None
    row = ff.public_row(claimed)
    assert row["kind"] == "fork-exploit" and row["revealed"] is False
    assert not {"target", "title", "severity", "program", "proof_sha256"} & set(row)
    row = ff.public_row(revealed)
    assert row["target"]["address"] == claimed["target"]["address"] and row["public_url"].startswith("https://")


def test_claims_export_and_verify_against_a_file(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    ff.save(a, _finding(tmp_path, attested_tx="0x" + "ab" * 32, attested_at="2026-11-07T00:00:00+00:00"))
    ff.save(b, _finding(tmp_path, severity="high"))  # a different claim: must not match
    out = tmp_path / "claims.json"
    assert cli.main(["claims", str(a), str(b), "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert len(data["claims"]) == 1 and data["claims"][0]["claim_tx"] == "0x" + "ab" * 32
    f = ff.load(a)
    claim = {"chain": "Robinhood Chain", "block": 1, "timestamp": 1, "from": SIGNER, "digest": "0x" + ff.digest(f).hex(),
             "registry": REGISTRY, "fee": chain.CLAIM_FEE, "burn_tx": None, "version": 3, "status": 1, "chain_id": 4663}
    db = os.path.join(tempfile.mkdtemp(), "m.db")
    with mock.patch.object(chain, "read_claim", return_value=claim), mock.patch.object(chain, "claim_problem", return_value=None):
        assert cli.main(["--db", db, "verify", "0x" + "ab" * 32, "--finding", str(a)]) == 0
        assert cli.main(["--db", db, "verify", "0x" + "ab" * 32, "--finding", str(b)]) == 1
    text = capsys.readouterr().out
    assert "finding file reproduces this claim" in text and "or the given files" in text


def test_hostile_reveals_and_files_are_refused(tmp_path, capsys):
    """Each of these broke a review probe before the fix; the input is the proof."""
    claim = bytes.fromhex("cd" * 32)
    good = chain.reveal_fields(_finding(tmp_path))
    # a swarm-shaped reveal that smuggles a proof hash: classified as a finding, then refused
    with pytest.raises(RuntimeError, match="finding reveal"):
        chain.decode_reveal(chain.encode_reveal(claim, {"risk": "r", "signature": "s", "proof_sha256": "x"}))
    # extra keys the digest never committed to, or a target written non-canonically: refused
    for bad in ({**good, "program": "famous"}, {**good, "target": {**good["target"], "repo": "x/y", "commit": "abcdef1"}},
                {**good, "target": {**good["target"], "address": good["target"]["address"].upper().replace("0X", "0x")}}):
        with pytest.raises(RuntimeError, match="finding reveal"):
            chain.decode_reveal(chain.encode_reveal(claim, bad))
    assert chain.decode_reveal(chain.encode_reveal(claim, good))["fields"] == good
    # trailing newline, a numeric path, a non-object file, a nested bomb, a bad tx hash
    f = _finding(tmp_path)
    for bad, msg in (({"target": {"repo": "a/b", "commit": "abcdef1\n"}}, "7 to 40 hex"),
                     ({"target": {"repo": "a/b", "commit": "abcdef1", "path": 1}}, "path must be a string"),
                     ({"proof_sha256": f["proof_sha256"] + "\n"}, "64 lowercase hex"),
                     ({"attested_tx": 5}, "attested_tx must be"), ({"revealed_tx": "0xab"}, "revealed_tx must be")):
        with pytest.raises(ValueError, match=msg):
            ff.validate({**f, **bad})
    (tmp_path / "list.json").write_text("[]")
    (tmp_path / "deep.json").write_text("[" * 100000)
    for name in ("list.json", "deep.json"):
        with pytest.raises(ValueError):
            ff.load(tmp_path / name)
    # quorum claims skips every bad file instead of dying on one
    out = tmp_path / "claims.json"
    assert cli.main(["claims", str(tmp_path / "list.json"), str(tmp_path / "deep.json"), "--out", str(out)]) == 1
    assert json.loads(out.read_text())["claims"] == []


def test_import_of_a_finding_reveal_checks_and_learns_nothing(tmp_path, capsys):
    f = _finding(tmp_path)
    r = {"fields": chain.reveal_fields(f), "revealed_by": SIGNER, "burn": None, "digest_matches": True,
         "same_signer": True, "fee_paid": True, "claim": {"status": 1}, "claim_tx": "0x" + "ab" * 32, "payment": None}
    db = os.path.join(tempfile.mkdtemp(), "m.db")
    with mock.patch.object(chain, "read_reveal", return_value=r), mock.patch.object(chain, "claim_problem", return_value=None):
        assert cli.main(["--db", db, "import", "0x" + "cd" * 32]) == 0
    text = capsys.readouterr().out
    assert "a paid finding claim" in text and "nothing to learn" in text


def test_reverted_reveal_is_not_written_to_the_file(tmp_path, capsys):
    path = tmp_path / "f.json"
    ff.save(path, _finding(tmp_path, attested_tx="0x" + "ab" * 32, status="fixed"))
    with mock.patch.object(chain, "_w3"), mock.patch.object(chain, "_account"), \
         mock.patch.object(chain, "_send", return_value={"tx": "0x" + "ee" * 32, "status": 0, "block": 1, "gas_used": 1}):
        assert cli.main(["reveal", "--finding", str(path)]) == 1
    assert json.loads(path.read_text())["revealed_tx"] is None
    assert "reverted" in capsys.readouterr().out
    # the same claim given twice is one claim
    dup = tmp_path / "dup.json"
    ff.save(dup, _finding(tmp_path))
    ff.save(path, _finding(tmp_path))
    dry = {"dry_run": True, "digest": "ab" * 32, "registry": REGISTRY}
    with mock.patch.object(chain, "attest", return_value=dry) as attest, mock.patch.object(chain, "token_balance", return_value=10**30), \
         mock.patch.object(chain, "address", return_value=SIGNER), mock.patch.object(chain, "balance_wei", return_value=10**18):
        assert cli.main(["attest", "--finding", str(path), str(dup), "--dry-run"]) == 0
        assert attest.call_count == 1
    assert "one digest is one claim" in capsys.readouterr().out
