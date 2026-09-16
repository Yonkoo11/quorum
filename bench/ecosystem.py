"""Run the eight lenses over every public Solidity repo HEY Research lists for Robinhood Chain.

    .venv/bin/python bench/ecosystem.py <workdir>            # list, clone (depth 1), scan, write <workdir>/ecosystem.json
    .venv/bin/python bench/ecosystem.py <workdir> --report   # ROBINHOOD.md from the json (findings read by hand afterwards)

Reads heyresearch.xyz/api (no key), asks GitHub which repos contain Solidity (gh api), clones each one
shallowly, scans every .sol outside tests, libraries, scripts and mocks with a fresh memory per repo,
and records every confirmed finding and every repo where nothing was confirmed. Nothing is uploaded;
public code is read and the result is written to one file.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quorum.agents import LENSES  # noqa: E402
from quorum.memory import SwarmMemory  # noqa: E402
from quorum.swarm import run_swarm  # noqa: E402

HEY = "https://heyresearch.xyz/api"
SKIP = ("/lib/", "/node_modules/", "/test/", "/tests/", "/script/", "/scripts/", "/mocks/", "/mock/", "/forge-std/", "/openzeppelin", "/.git/")


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "quorum-ecosystem-run", "accept": "application/json"})
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(2 + attempt * 3)


def list_projects() -> list[dict]:
    """HEY caps a page at 48 items and returns nextOffset until the listing is done."""
    out, offset = [], 0
    while True:
        d = get(f"{HEY}/projects?has=github&limit=48&offset={offset}")
        items = d.get("items") or []
        out.extend(items)
        nxt = d.get("nextOffset")
        if not items or nxt is None or nxt <= offset:
            break
        offset = nxt
        time.sleep(0.6)
    seen, uniq = set(), []
    for p in out:
        if p["slug"] not in seen:
            seen.add(p["slug"]); uniq.append(p)
    return uniq


def repos_of(slug: str) -> list[str]:
    """Every distinct owner/name GitHub repo in the project's HEY sources (a project may list several)."""
    det = get(f"{HEY}/projects/{slug}")
    out = []
    for src in det.get("sources") or []:
        m = re.match(r"https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", str(src.get("url", "")))
        if m and m.group(2).lower() not in ("orgs",) and f"{m.group(1)}/{m.group(2)}" not in out:
            out.append(f"{m.group(1)}/{m.group(2)}")
    return out


def has_solidity(repo: str) -> bool:
    r = subprocess.run(["gh", "api", f"repos/{repo}/languages"], capture_output=True, text=True)
    try:
        langs = json.loads(r.stdout)
    except json.JSONDecodeError:
        return False
    return isinstance(langs, dict) and ("Solidity" in langs or "Vyper" in langs)


def clone(repo: str, dest: Path) -> bool:
    if dest.exists():
        return True
    r = subprocess.run(["git", "clone", "--quiet", "--depth", "1", f"https://github.com/{repo}.git", str(dest)],
                       capture_output=True, text=True, timeout=300)
    return r.returncode == 0


def scan(dest: Path, db: Path) -> dict:
    files = [f for f in dest.rglob("*.sol") if not any(s in ("/" + str(f.relative_to(dest)).lower() + "/") for s in SKIP)]
    targets = {}
    for f in files:
        try:
            targets[str(f.relative_to(dest))] = f.read_text(errors="replace")
        except OSError:
            continue
    if not targets:
        return {"files": 0, "confirmed": [], "candidates": 0, "scanned": 0}
    report = run_swarm(SwarmMemory(str(db)), targets)
    return {"files": len(targets), "scanned": report.scanned, "candidates": len(report.candidates),
            "confirmed": [{"key": f"{c['contract']}:{c['function']}:{c['risk']}", "seen_by": c.get("seen_by", []),
                           "evidence": (c.get("evidence") or "")[:160]} for c in report.promoted]}


def main(work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    state_path = work / "ecosystem.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"projects": {}, "started": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    projects = list_projects()
    print(f"{len(projects)} projects with a public repo", flush=True)
    for i, p in enumerate(projects):
        slug = p["slug"]
        if slug in state["projects"] and state["projects"][slug].get("done"):
            continue
        rec = {"name": p.get("name"), "kind": p.get("projectKind"), "repos": {}}
        try:
            for repo in repos_of(slug):
                r: dict = {}
                if not has_solidity(repo):
                    r["skip"] = "no solidity"
                else:
                    dest = work / "repos" / repo.replace("/", "__")
                    (work / "dbs").mkdir(exist_ok=True)
                    if not clone(repo, dest):
                        r["skip"] = "clone failed"
                    else:
                        r.update(scan(dest, work / "dbs" / (repo.replace("/", "__") + ".db")))
                rec["repos"][repo] = r
            if not rec["repos"]:
                rec["skip"] = "no repo url"
        except Exception as e:  # noqa: BLE001
            rec["skip"] = f"error: {str(e)[:80]}"
        rec["done"] = True
        state["projects"][slug] = rec
        state_path.write_text(json.dumps(state, indent=1))
        line = rec.get("skip") or "; ".join(f"{k}: " + (v.get("skip") or f"{v['files']} files, {len(v['confirmed'])} confirmed, {v['candidates']} candidates") for k, v in rec["repos"].items())
        print(f"[{i + 1}/{len(projects)}] {slug}: {line}", flush=True)
        time.sleep(0.5)
    print("done", flush=True)


def report(work: Path) -> None:
    state = json.loads((work / "ecosystem.json").read_text())
    ps = state["projects"]
    repos = {}
    for slug, v in ps.items():
        for repo, r in (v.get("repos") or {}).items():
            repos.setdefault(repo, r)
    scanned = {k: v for k, v in repos.items() if v.get("files", 0) > 0}
    with_findings = {k: v for k, v in scanned.items() if v["confirmed"]}
    skips = {}
    for v in list(ps.values()) + list(repos.values()):
        if v.get("skip"):
            skips[v["skip"].split(":")[0]] = skips.get(v["skip"].split(":")[0], 0) + 1
    print("# Every public Solidity repo on Robinhood Chain, scanned\n")
    print(f"Run started {state['started']}. Listing: heyresearch.xyz/api, projects with a public GitHub repo, every GitHub repo in each project's sources. Repos whose GitHub language list includes Solidity or Vyper were cloned at depth 1 and read by the eight lenses with a fresh memory per repo; tests, libraries, scripts and mocks excluded. Command: `python bench/ecosystem.py <workdir>`.\n")
    print("| | count |\n|---|---|")
    print(f"| projects HEY lists with a public repo | {len(ps)} |")
    print(f"| distinct GitHub repos in their sources | {len(repos)} |")
    print(f"| repos containing Solidity, cloned and scanned | {len(scanned)} |")
    print(f"| Solidity files read | {sum(v['files'] for v in scanned.values()):,} |")
    print(f"| lens-units scanned | {sum(v['scanned'] for v in scanned.values()):,} |")
    print(f"| findings confirmed (two lenses agreed) | {sum(len(v['confirmed']) for v in scanned.values())} |")
    print(f"| candidates held back (one lens only) | {sum(v['candidates'] for v in scanned.values()):,} |")
    print(f"| repos with at least one confirmed finding | {len(with_findings)} |")
    print(f"| repos where nothing was confirmed | {len(scanned) - len(with_findings)} |")
    for k, n in sorted(skips.items()):
        print(f"| skipped: {k} | {n} |")
    print("\n## Confirmed findings, one line each, to be read by hand\n")
    for repo, v in sorted(with_findings.items()):
        for c in v["confirmed"]:
            print(f"- `{repo}` `{c['key']}` ({', '.join(c['seen_by'])}): `{c['evidence'][:100]}`")


if __name__ == "__main__":
    w = Path(sys.argv[1])
    if "--report" in sys.argv:
        report(w)
    else:
        main(w)
