#!/usr/bin/env python3
"""Rebuild the recent-audit-contest corpus that bench/modern.py measures.

    python bench/fetch_modern.py <workdir>

Clones each Code4rena contest repo named in bench/labels/modern-c4.json at the exact commit pinned
there, into <workdir>/<contest>. That is the whole point: MODERN.md used to name sixteen contests and
record neither the repository nor the commit, so its numbers could not be re-derived by anyone,
including us. The other two corpora have had a clone one-liner in bench/README.md since the start.

The contest repos are still live and have been pushed to since their audits, so the pinned commit,
not the branch head, is what makes a re-run comparable.
"""
import json
import subprocess
import sys
from pathlib import Path

LABELS = Path(__file__).parent / "labels" / "modern-c4.json"


def clone(repo: str, commit: str, dest: Path) -> bool:
    """Shallow-fetch exactly one commit. Cheaper than a full clone and pins what we measured."""
    if (dest / ".git").exists():
        head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        if head == commit:
            return True
        subprocess.run(["rm", "-rf", str(dest)], check=False)
    dest.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{repo}.git"
    for cmd in (["git", "-C", str(dest), "init", "-q"],
                ["git", "-C", str(dest), "remote", "add", "origin", url],
                ["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", commit],
                ["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"]):
        if subprocess.run(cmd, capture_output=True, text=True).returncode != 0:
            return False
    return True


def main(work: Path) -> int:
    spec = json.loads(LABELS.read_text())
    repos = spec.get("repos")
    if not repos:
        print("no `repos` manifest in the label file", file=sys.stderr)
        return 1
    # bench/modern.py reads <workdir>/repos/<contest>, so clone into the layout it expects.
    root = work / "repos"
    root.mkdir(parents=True, exist_ok=True)
    failed = []
    for i, (contest, r) in enumerate(sorted(repos.items()), 1):
        dest = root / contest
        ok = clone(r["repo"], r["commit"], dest)
        n = len(list(dest.rglob("*.sol"))) if ok else 0
        print(f"[{i}/{len(repos)}] {contest}: {'ok' if ok else 'FAILED'} ({n} .sol)", flush=True)
        if not ok:
            failed.append(contest)
    if failed:
        print(f"\nfailed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\n{len(repos)} contests in {work}. Now:\n"
          f"  python bench/modern.py {work} --labels bench/labels/modern-c4.json > bench/MODERN.md")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
