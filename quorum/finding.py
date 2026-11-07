"""A finding file: one security finding, from any tool, that Quorum can claim on chain.

The registry stores a 32-byte digest and burns the fee; it never sees what the digest is
of. So anything with a reproducible proof can be claimed, not only what the swarm found.
The file is the contract between the finder (bughunter, a fuzz harness, a hand audit) and
the claim: the finder writes it, `quorum attest --finding` claims it, `quorum reveal
--finding` discloses it once the fix is public.

    {
      "quorum": 2,
      "kind": "fork-exploit" | "failing-test" | "counterexample" | "write-up",
      "title": "First depositor share inflation in CToken",
      "target": {"chain": "ethereum", "address": "0x..."}          # on-chain target
               | {"repo": "ZcashFoundation/zebra", "commit": "e6644c2", "path": "zebra-fuzz/fuzz/Cargo.toml"},
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "proof_sha256": "<sha256 of the proof file: the PoC test, the counterexample, the write-up>",
      "proof_file": "capyfi-first-depositor-POC.t.sol",           # local name, not committed
      "program": "immunefi",                                       # where it was or will be reported
      "found_at": "2026-11-07",
      "status": "committed" | "reported" | "fixed" | "revealed",
      "public_url": null,                                          # the public issue or PR, once there is one
      "attested_tx": null, "attested_at": null, "revealed_tx": null
    }

Committed to the digest: kind, target, severity, proof_sha256. Nothing else. The title,
the program and the local file name stay off chain. The timestamp of the claim proves
priority; the reveal proves what was claimed; the proof file, published with the fix,
proves it was real, because anyone can hash it and compare.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from web3 import Web3

VERSION = 2
KINDS = ("fork-exploit", "failing-test", "counterexample", "write-up")
SEVERITIES = ("critical", "high", "medium", "low", "info")
STATUSES = ("committed", "reported", "fixed", "revealed")
REVEALABLE = ("fixed", "revealed")  # a reveal before the fix is public is a disclosure, not a claim
_SHA256 = re.compile(r"[0-9a-f]{64}")
_ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
_TX = re.compile(r"0x[0-9a-fA-F]{64}")
_COMMIT = re.compile(r"[0-9a-f]{7,40}")


def sha256_of(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def is_finding(obj: dict[str, Any]) -> bool:
    """A v2 finding carries a proof hash; a swarm finding carries a risk and a signature."""
    return isinstance(obj, dict) and "proof_sha256" in obj


def canonical_target(target: Any) -> dict[str, str]:
    """The target as it is hashed: lowercase address, or repo + commit (+ path)."""
    if not isinstance(target, dict):
        raise ValueError("target must be an object")
    if "address" in target:
        chain, address = target.get("chain"), target.get("address")
        if not isinstance(chain, str) or not chain:
            raise ValueError("an on-chain target needs a chain name")
        if not isinstance(address, str) or not _ADDRESS.fullmatch(address):
            raise ValueError("an on-chain target needs a 0x address of 40 hex digits")
        return {"chain": chain.lower(), "address": address.lower()}
    repo, commit = target.get("repo"), target.get("commit")
    if not isinstance(repo, str) or "/" not in repo:
        raise ValueError("a code target needs a repo as owner/name")
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise ValueError("a code target needs a commit hash of 7 to 40 hex digits")
    out = {"repo": repo, "commit": commit}
    path = target.get("path")
    if path is not None and path != "":
        if not isinstance(path, str):
            raise ValueError("a code target's path must be a string")
        out["path"] = path
    return out


def validate(f: dict[str, Any]) -> dict[str, Any]:
    """Raise ValueError naming the first thing wrong; return the finding with its target canonical."""
    if f.get("quorum") != VERSION:
        raise ValueError(f'"quorum" must be {VERSION}')
    if f.get("kind") not in KINDS:
        raise ValueError(f'kind must be one of {", ".join(KINDS)}')
    if f.get("severity") not in SEVERITIES:
        raise ValueError(f'severity must be one of {", ".join(SEVERITIES)}')
    if not isinstance(f.get("proof_sha256"), str) or not _SHA256.fullmatch(f["proof_sha256"]):
        raise ValueError("proof_sha256 must be 64 lowercase hex digits")
    if not isinstance(f.get("title"), str) or not f["title"].strip():
        raise ValueError("title must be a non-empty string")
    if f.get("status", "committed") not in STATUSES:
        raise ValueError(f'status must be one of {", ".join(STATUSES)}')
    for key in ("attested_tx", "revealed_tx"):
        if f.get(key) is not None and not (isinstance(f[key], str) and _TX.fullmatch(f[key])):
            raise ValueError(f"{key} must be null or a 0x transaction hash of 64 hex digits")
    if f.get("attested_at") is not None and not isinstance(f["attested_at"], str):
        raise ValueError("attested_at must be null or a string")
    return {**f, "target": canonical_target(f.get("target"))}


def digest_fields(f: dict[str, Any]) -> dict[str, Any]:
    """Exactly what the claim commits to. Order-free: the JSON is sorted when hashed."""
    return {"kind": f["kind"], "target": canonical_target(f["target"]),
            "severity": f["severity"], "proof_sha256": f["proof_sha256"]}


def digest(f: dict[str, Any]) -> bytes:
    payload = json.dumps(digest_fields(f), sort_keys=True, separators=(",", ":"))
    return Web3.keccak(text=payload)


def revealed_fields_ok(fields: dict[str, Any]) -> bool:
    """Shape check for a reveal read back from chain, before anything is recomputed from it.

    The fields must be exactly what a digest commits to, already canonical: a reveal that
    carries extra keys, or a target written differently from how it was hashed, is refused,
    so nothing can be shown that the digest did not commit to."""
    try:
        validate({**fields, "quorum": VERSION, "title": "revealed"})
        return fields == digest_fields(fields)
    except ValueError:
        return False


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        f = json.loads(p.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"{p}: not a readable JSON file ({exc.__class__.__name__})") from exc
    if not isinstance(f, dict):
        raise ValueError(f"{p}: a finding file is a JSON object")
    try:
        return validate(f)
    except ValueError as exc:
        raise ValueError(f"{p}: {exc}") from exc


def save(path: str | Path, f: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(f, indent=2, sort_keys=False) + "\n")


def new(title: str, kind: str, target: dict[str, Any], severity: str, proof_path: str | Path,
        program: str | None = None, found_at: str | None = None) -> dict[str, Any]:
    """Build a finding from a proof file on disk. The hash is taken now; the file must not change after."""
    proof = Path(proof_path)
    if not proof.is_file():
        raise ValueError(f"proof file not found: {proof}")
    f = {
        "quorum": VERSION,
        "kind": kind,
        "title": title,
        "target": target,
        "severity": severity,
        "proof_sha256": sha256_of(proof),
        "proof_file": proof.name,
        "program": program,
        "found_at": found_at or datetime.now(timezone.utc).date().isoformat(),
        "status": "committed",
        "public_url": None,
        "attested_tx": None,
        "attested_at": None,
        "revealed_tx": None,
    }
    return validate(f)


def public_row(f: dict[str, Any]) -> dict[str, Any] | None:
    """What the registry page may show. Before the reveal: the kind and the claim, nothing that
    points at the target. After it: the fields that were revealed, and the public link."""
    if not f.get("attested_tx"):
        return None
    row = {"kind": f["kind"], "digest": "0x" + digest(f).hex(), "claim_tx": f["attested_tx"],
           "claimed_at": f.get("attested_at"), "revealed": bool(f.get("revealed_tx"))}
    if f.get("revealed_tx"):
        row.update({"title": f["title"], "target": canonical_target(f["target"]), "severity": f["severity"],
                    "proof_sha256": f["proof_sha256"], "reveal_tx": f["revealed_tx"],
                    "public_url": f.get("public_url"), "program": f.get("program")})
    return row
