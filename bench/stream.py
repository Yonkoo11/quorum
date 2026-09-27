"""The live blind benchmark: every hack reproduced after the freeze is a test nobody has tuned for.

    python bench/stream.py intake  <DeFiHackLabs clone> <workdir>   # new hacks -> victim source
    python bench/stream.py predict <contestant> <workdir> [--set dev|stream]
    python bench/stream.py label   <DeFiHackLabs clone> <workdir>
    python bench/stream.py score   [--set dev|stream]               # the table, to stdout

Every earlier corpus here stopped being a test once a lens was built from its misses. This one
cannot: `labels/stream-freeze.txt` lists the 861 proofs of concept that existed at DeFiHackLabs
commit 0520ddb (2026-09-27), and only a proof of concept added after that is admitted.

Three roles, each kept from what it must not see. Intake reads the proof of concept and returns the
victim's chain and address, nothing else. A contestant sees only the victim's source, renamed
`target.sol`. The labeller reads the proof of concept's root-cause note and the source, never a
prediction. The order is enforced here, not trusted: predict refuses an entry that has a label,
label refuses an entry some contestant has not predicted, and score drops any prediction written
after its label.

Model calls go through the `claude` CLI with the caller's own settings and every web tool off.
If an API key in the environment overrides the login, run the whole command under
`env -u ANTHROPIC_API_KEY`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quorum import targets as fetcher  # noqa: E402
from quorum.agents import LENSES, Project  # noqa: E402
from quorum.memory import QUORUM_THRESHOLD  # noqa: E402
from quorum.swarm import split_witness  # noqa: E402

HERE = Path(__file__).parent
STREAM = HERE / "labels" / "stream.json"
FREEZE = HERE / "labels" / "stream-freeze.txt"
PREDICTIONS = HERE / "stream" / "predictions"
JUDGMENTS = HERE / "stream" / "judgments"
PASHOV = Path.home() / "Projects" / "pashov-skills" / "solidity-auditor"   # pashov/skills, pinned by tag
V4_THRESHOLD = 75
NO_WEB = ["--disallowedTools", "WebSearch", "WebFetch"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load() -> dict:
    return json.loads(STREAM.read_text())


def save(data: dict) -> None:
    STREAM.write_text(json.dumps(data, indent=1) + "\n")


def slug(entry_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", entry_id)


def claude(prompt: str, cwd: Path, tools: str, timeout: int = 3600) -> dict:
    """One headless model call confined to `cwd`. Returns the CLI's JSON result or raises."""
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--setting-sources", "project,local",
           "--strict-mcp-config", "--permission-mode", "acceptEdits", "--allowedTools", tools, *NO_WEB]
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    try:
        result = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude returned no JSON: {out.stderr[-300:]}") from None
    if result.get("is_error"):
        raise RuntimeError(f"claude failed: {str(result.get('result'))[:300]}")
    return result


def json_block(text: str):
    """The last JSON value in a model's answer, fenced or bare."""
    fenced = re.findall(r"```(?:json)?\s*(.+?)```", text, re.S)
    for chunk in reversed(fenced + [text]):
        for start in (chunk.find("["), chunk.find("{")):
            if start >= 0:
                try:
                    return json.loads(chunk[start:chunk.rfind("]" if chunk[start] == "[" else "}") + 1])
                except json.JSONDecodeError:
                    continue
    raise ValueError("no JSON in answer")


# --------------------------------------------------------------------------- intake

INTAKE_PROMPT = """Read {poc}. It reproduces a smart-contract exploit. Return two addresses, because a
proof needs both and they are often different:
  - `address`: the contract whose SOURCE holds the vulnerable logic (the implementation or facet). This
    is where the bug is read from.
  - `proxy`: the deployed contract the users actually funded and the attacker calls (the proxy in front
    of that implementation, or the same address when there is no proxy). This is where the state is.
Neither is a token the attacker only traded, nor the attacker's own contract. Also give `block`, the
fork block the proof of concept uses (the exploit's parent block; resolve any named constant to its
number). Answer with JSON only:
{{"chain": "<ethereum|base|arbitrum|optimism|polygon|bsc|other>", "address": "0x...", "proxy": "0x...", "block": <number>, "name": "<contract name>"}}
Do not describe the bug. If no single victim contract is named, answer {{"chain": "none"}}."""


def new_pocs(dhl: Path, data: dict) -> list[str]:
    frozen = set(FREEZE.read_text().split())
    seen = {e["poc"] for e in data["entries"]}
    found = sorted(str(p.relative_to(dhl)) for p in (dhl / "src" / "test").rglob("*_exp.sol"))
    return [p for p in found if p not in frozen and p not in seen]


def intake_one(dhl: Path, work: Path, poc: str) -> dict:
    entry = {"id": Path(poc).stem.removesuffix("_exp"), "poc": poc, "set": "stream", "intake_at": now()}
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(dhl / poc, Path(tmp) / "poc.sol")
        victim = json_block(claude(INTAKE_PROMPT.format(poc="poc.sol"), Path(tmp), "Read")["result"])
    victim = {k: victim.get(k) for k in ("chain", "address", "proxy", "block", "name")}  # nothing else leaves intake
    victim["proxy"] = victim.get("proxy") or victim.get("address")               # same address when no proxy
    entry.update(victim)
    if victim["chain"] not in fetcher.SOURCE_CHAINS:
        return {**entry, "status": f"skipped: chain {victim['chain']}"}
    try:
        name, code = fetcher.fetch_source(victim["address"], victim["chain"], timeout=60)
    except Exception as exc:                          # unverified, or an explorer that is down today
        return {**entry, "status": f"skipped: {str(exc)[-80:]}"}
    path = work / "src" / f"{slug(entry['id'])}.sol"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    return {**entry, "name": name, "sha256": hashlib.sha256(code.encode()).hexdigest(), "status": "fetched"}


def intake(dhl: Path, work: Path) -> None:
    data = load()
    for poc in new_pocs(dhl, data):
        entry = intake_one(dhl, work, poc)
        data["entries"].append(entry)
        save(data)
        print(f"{entry['status']:>10}  {poc}")


# --------------------------------------------------------------------------- contestants

GENERIC_PROMPT = """You are a smart-contract security auditor. Audit target.sol, a deployed contract
flattened with its dependencies; focus on the project's own contracts, not library code. Report the
findings that let an unprivileged attacker take or lock funds (Critical/High only), at most 5, as a
JSON list only: [{"contract": "...", "function": "<external entry point>", "confidence": 0-100,
"text": "<one sentence: the attack>"}]. An empty list is a valid answer."""


def regex_v0(iso: Path) -> tuple[list[dict], float]:
    """The frozen regex engine, under the swarm's own rule: two distinct lenses on one key."""
    src = (iso / "target.sol").read_text(errors="replace")
    project, seen, lines = Project.read({"target.sol": src}), {}, {}
    for lens_name, lens in LENSES.items():
        for s in lens("target.sol", src, project):
            key = (s.function, s.risk)
            seen.setdefault(key, set()).add(lens_name)
            lines.setdefault(key, set()).add(s.line)
    found = [{"contract": "", "function": fn, "confidence": 100, "tier": "finding",
              "text": f"{risk}, corroborated by {', '.join(sorted(seen[(fn, risk)]))}"}
             for (fn, risk) in sorted(seen)
             if len(seen[(fn, risk)]) >= QUORUM_THRESHOLD and not split_witness(risk, lines[(fn, risk)])]
    return found, 0.0


def generic(iso: Path) -> tuple[list[dict], float]:
    res = claude(GENERIC_PROMPT, iso, "Read Grep Glob")
    found = [{**f, "tier": "finding"} for f in json_block(res["result"])]
    return found, res.get("total_cost_usd", 0.0)


V4_FINDING = re.compile(r"^\[(\d+)\] \*\*\d+\. (.+?)\*\*\s*\n\s*\n`([\w$]+)\.([\w$]+)`", re.M)
V4_LEAD = re.compile(r"^- \*\*(.+?)\*\* — `([\w$]+)\.([\w$]+)` — (.+)$", re.M)


def parse_v4(report: str) -> list[dict]:
    """v4's report is emitted by its own shell assembler, so its shape is a contract, not prose."""
    body, _, leads = report.partition("\n## Leads")
    out = [{"contract": c, "function": f, "confidence": int(conf), "text": title,
            "tier": "finding" if int(conf) >= V4_THRESHOLD else "below-threshold"}
           for conf, title, c, f in V4_FINDING.findall(body)]
    out += [{"contract": c, "function": f, "confidence": 0, "text": f"{title}: {rest[:300]}", "tier": "lead"}
            for title, c, f, rest in V4_LEAD.findall(leads)]
    return out


def v4_one_pass(iso: Path) -> tuple[list[dict], float]:
    shutil.copytree(PASHOV, iso / ".claude" / "skills" / "solidity-auditor")
    subprocess.run(["git", "init", "-q"], cwd=iso, check=True)
    res = claude("/solidity-auditor --loop 1", iso, "Bash Read Write Edit Glob Grep Agent ToolSearch Skill")
    reports = sorted(iso.glob(".solidity-auditor/runs/*/full-report.md"))
    if not reports:
        raise RuntimeError("v4 wrote no report")
    return parse_v4(reports[-1].read_text()), res.get("total_cost_usd", 0.0)


def v4_version() -> str:
    tag = subprocess.run(["git", "describe", "--tags"], cwd=PASHOV, capture_output=True, text=True)
    return f"pashov/skills {tag.stdout.strip() or 'untagged'}"


CONTESTANTS = {"regex-v0": (regex_v0, lambda: "quorum v0.7.1 lenses"),
               "generic": (generic, lambda: "claude -p, one prompt"),
               "v4-1pass": (v4_one_pass, v4_version)}


# --------------------------------------------------------------------------- predict

def prediction_path(contestant: str, entry: dict) -> Path:
    return PREDICTIONS / contestant / f"{slug(entry['id'])}.json"


def predict_one(contestant: str, entry: dict, work: Path) -> dict:
    run, version = CONTESTANTS[contestant]
    with tempfile.TemporaryDirectory() as tmp:
        iso = Path(tmp)
        shutil.copy(work / "src" / f"{slug(entry['id'])}.sol", iso / "target.sol")
        started = time.time()
        findings, cost = run(iso)
    return {"entry": entry["id"], "contestant": contestant, "version": version(),
            "source_sha256": entry["sha256"], "predicted_at": now(),
            "seconds": round(time.time() - started), "cost_usd": round(cost, 2), "findings": findings}


def predict(contestant: str, work: Path, which: str) -> None:
    for entry in [e for e in load()["entries"] if e["set"] == which and e["status"] == "fetched"]:
        path = prediction_path(contestant, entry)
        if entry.get("label") and entry["set"] == "stream":   # dev labels predate everything, openly
            print(f"refused   {entry['id']}: already labelled, a prediction now would not be blind")
            continue
        if path.exists():
            continue
        try:
            pred = predict_one(contestant, entry, work)
        except Exception as exc:                      # a failed run is recorded as nothing, never as a miss
            print(f"failed    {entry['id']}: {exc}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(pred, indent=1) + "\n")
        print(f"predicted {entry['id']}: {len(pred['findings'])} item(s), ${pred['cost_usd']}")


# --------------------------------------------------------------------------- label

LABEL_PROMPT = """poc.sol reproduces an exploit of the contract in target.sol. Read the proof of concept's
root-cause notes and confirm them against target.sol. Answer with JSON only:
{"entry_points": ["Contract.function", ...], "class": "<access-control|reentrancy|arithmetic|accounting-mismatch|price-manipulation|logic-other>",
 "mechanism": "<two sentences: the root cause and how the attacker used it>"}
entry_points are the functions an attacker calls to reach the bug, and the function that holds it."""


def label(dhl: Path, work: Path, contestants: list[str]) -> None:
    data = load()
    for entry in [e for e in data["entries"] if e["status"] == "fetched" and not e.get("label")]:
        missing = [c for c in contestants if not prediction_path(c, entry).exists()]
        if missing:
            print(f"waiting   {entry['id']}: no prediction yet from {', '.join(missing)}")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(dhl / entry["poc"], Path(tmp) / "poc.sol")
            shutil.copy(work / "src" / f"{slug(entry['id'])}.sol", Path(tmp) / "target.sol")
            found = json_block(claude(LABEL_PROMPT, Path(tmp), "Read Grep")["result"])
        entry["label"] = {**found, "labelled_at": now(), "labelled_by": "claude -p, after every prediction"}
        save(data)
        print(f"labelled  {entry['id']}: {found.get('class')}")


# --------------------------------------------------------------------------- score

JUDGE_PROMPT = """A hack's true root cause:
{label}

A tool's findings on that contract, numbered:
{findings}

For each finding answer "strict" if it names the same root cause (wording and function may differ),
"surfacing" if it points at the right code for a related but incomplete or different reason, or "none".
Answer with a JSON list of verdicts only, one per finding, in order."""


def judge(entry: dict, pred: dict) -> list[str]:
    """One judged verdict per finding, cached so a re-score costs nothing and cannot drift."""
    items = "\n".join(f"{i + 1}. {f['contract']}.{f['function']}: {f['text']}" for i, f in enumerate(pred["findings"]))
    lab = entry["label"]
    ask = JUDGE_PROMPT.format(label=f"{', '.join(lab['entry_points'])}: {lab['mechanism']}", findings=items)
    key = hashlib.sha256(ask.encode()).hexdigest()[:16]
    cache = JUDGMENTS / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text())["verdicts"]
    if not pred["findings"]:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        verdicts = json_block(claude(ask, Path(tmp), "Read")["result"])
    if len(verdicts) != len(pred["findings"]):
        raise ValueError(f"judge gave {len(verdicts)} verdicts for {len(pred['findings'])} findings")
    JUDGMENTS.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"entry": entry["id"], "contestant": pred["contestant"], "verdicts": verdicts}) + "\n")
    return verdicts


def tally(entries: list[dict], contestant: str) -> dict | None:
    row = {"entries": 0, "any": 0, "strict_any": 0, "strict_top": 0, "items": 0, "hits": 0, "cost": 0.0}
    for entry in entries:
        path = prediction_path(contestant, entry)
        if not path.exists():
            continue
        pred = json.loads(path.read_text())
        if entry["set"] == "stream" and pred["predicted_at"] >= entry["label"]["labelled_at"]:
            print(f"dropped: {contestant} predicted {entry['id']} after its label", file=sys.stderr)
            continue
        verdicts = judge(entry, pred)
        pairs = list(zip(pred["findings"], verdicts))
        row["entries"] += 1
        row["any"] += any(v in ("strict", "surfacing") for _, v in pairs)
        row["strict_any"] += any(v == "strict" for _, v in pairs)
        row["strict_top"] += any(v == "strict" and f["tier"] == "finding" for f, v in pairs)
        row["items"] += len(pairs)
        row["hits"] += sum(v in ("strict", "surfacing") for _, v in pairs)
        row["cost"] += pred["cost_usd"]
    return row if row["entries"] else None


def score(which: str) -> None:
    entries = [e for e in load()["entries"] if e["set"] == which and e.get("label")]
    print(f"# The stream, set `{which}`: {len(entries)} labelled hack(s)\n")
    print("| contestant | hacks run | root cause found, any tier | exact root cause | exact, top tier only "
          "| items written | items on the root cause | cost |")
    print("|---|---|---|---|---|---|---|---|")
    for name in CONTESTANTS:
        r = tally(entries, name)
        if r:
            print(f"| {name} | {r['entries']} | {r['any']} | {r['strict_any']} | {r['strict_top']} "
                  f"| {r['items']} | {r['hits']} | ${r['cost']:.2f} |")
    print("\nAn item that is not on the labelled root cause counts against its tool even when it may be a "
          "real, different bug; nobody has checked those yet.")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="The live blind benchmark.")
    ap.add_argument("command", choices=["intake", "predict", "label", "score"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--set", default="stream", choices=["dev", "stream"])
    a = ap.parse_args(argv)
    if a.command == "intake":
        intake(Path(a.args[0]), Path(a.args[1]))
    elif a.command == "predict":
        predict(a.args[0], Path(a.args[1]), a.set)
    elif a.command == "label":
        label(Path(a.args[0]), Path(a.args[1]), load()["contestants"])
    else:
        score(a.set)


if __name__ == "__main__":
    main()
