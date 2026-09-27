import json

import pytest

from bench import stream

V4_REPORT = """# Security Review — x

## Findings

[95] **1. Any launch caller removes the liquidity of every earlier launch**

`LaunchpadFactoryAuto.launch` · Confidence: 95

**Description**
text

[70] **2. solve takes want tokens from any contract that the caller names**

`AtomicQueue.solve` · Confidence: 70

---

## Leads

- **The init flag may stay set for the whole deploy transaction** — `StartaleSmartAccount.initializeAccount` — Code smells: no code clears it — A later call may re-initialize.
"""


def test_every_tier_of_a_v4_report_is_kept():
    """Leads and below-threshold items are where v4 put two of the real hacks it alone surfaced."""
    got = stream.parse_v4(V4_REPORT)
    assert [(f["function"], f["tier"]) for f in got] == [
        ("launch", "finding"), ("solve", "below-threshold"), ("initializeAccount", "lead")]


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(stream, "STREAM", tmp_path / "stream.json")
    monkeypatch.setattr(stream, "PREDICTIONS", tmp_path / "predictions")
    monkeypatch.setattr(stream, "JUDGMENTS", tmp_path / "judgments")
    entry = {"id": "Hack", "poc": "src/test/2026-10/Hack_exp.sol", "set": "stream", "status": "fetched",
             "sha256": "x", "label": {"entry_points": ["C.f"], "class": "logic-other", "mechanism": "m",
                                      "labelled_at": "2026-10-02T00:00:00+00:00"}}
    stream.save({"contestants": ["regex-v0"], "entries": [entry]})
    return tmp_path, entry


def test_a_labelled_stream_hack_cannot_be_predicted(ledger, capsys):
    tmp, _ = ledger
    stream.predict("regex-v0", tmp, "stream")
    assert "refused" in capsys.readouterr().out
    assert not (tmp / "predictions").exists()


def test_a_prediction_written_after_its_label_is_not_scored(ledger, capsys):
    tmp, entry = ledger
    late = {"entry": "Hack", "contestant": "regex-v0", "predicted_at": "2026-10-03T00:00:00+00:00",
            "cost_usd": 0, "findings": []}
    path = stream.prediction_path("regex-v0", entry)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(late))
    assert stream.tally([entry], "regex-v0") is None
    assert "after its label" in capsys.readouterr().err


def test_labelling_waits_for_every_contestant(ledger, capsys):
    tmp, entry = ledger
    del entry["label"]
    stream.save({"contestants": ["regex-v0"], "entries": [entry]})
    stream.label(tmp, tmp, ["regex-v0"])
    assert "waiting" in capsys.readouterr().out
    assert "label" not in stream.load()["entries"][0]


def test_intake_passes_on_nothing_but_the_victim(monkeypatch, tmp_path):
    """Intake reads the root-cause note, so anything else it says must not reach the ledger."""
    (tmp_path / "src" / "test" / "2026-10").mkdir(parents=True)
    (tmp_path / "src" / "test" / "2026-10" / "Hack_exp.sol").write_text("// poc")
    answer = '{"chain": "ethereum", "address": "0xabc", "name": "V", "root_cause": "leak"}'
    monkeypatch.setattr(stream, "claude", lambda *a, **k: {"result": answer})
    monkeypatch.setattr(stream.fetcher, "fetch_source", lambda *a, **k: ("V", "contract V {}"))
    entry = stream.intake_one(tmp_path, tmp_path / "work", "src/test/2026-10/Hack_exp.sol")
    assert "root_cause" not in entry and entry["status"] == "fetched"


def test_intake_records_the_proxy_and_block_for_proving(monkeypatch, tmp_path):
    """A proof forks at the proxy (funds) and block; intake must capture both, and default the proxy
    to the implementation when the note names no separate one."""
    (tmp_path / "src" / "test" / "2026-10").mkdir(parents=True)
    (tmp_path / "src" / "test" / "2026-10" / "H_exp.sol").write_text("// poc")
    monkeypatch.setattr(stream.fetcher, "fetch_source", lambda *a, **k: ("V", "contract V {}"))

    both = '{"chain":"base","address":"0xIMPL","proxy":"0xPROXY","block":123,"name":"V"}'
    monkeypatch.setattr(stream, "claude", lambda *a, **k: {"result": both})
    e = stream.intake_one(tmp_path, tmp_path / "w1", "src/test/2026-10/H_exp.sol")
    assert e["address"] == "0xIMPL" and e["proxy"] == "0xPROXY" and e["block"] == 123

    no_proxy = '{"chain":"base","address":"0xONLY","block":9,"name":"V"}'
    monkeypatch.setattr(stream, "claude", lambda *a, **k: {"result": no_proxy})
    e = stream.intake_one(tmp_path, tmp_path / "w2", "src/test/2026-10/H_exp.sol")
    assert e["proxy"] == "0xONLY"
