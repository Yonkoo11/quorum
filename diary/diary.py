"""The diary: what the repo did, told to the Telegram group in plain words.

Runs from .github/workflows/diary.yml every two hours. Each run covers the time
since the previous successful run's window closed, on a clock aligned to two-hour
steps, so a skipped or delayed run is covered by the next one and nothing is posted
twice. There is no database.

    python diary/diary.py --dry --hours 48     # print what would be posted, post nothing
    python diary/diary.py                      # the scheduled run

Environment: GITHUB_REPO (owner/name), GITHUB_TOKEN (given by Actions; optional
locally), the writer key, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID. The writer uses
Google's free-tier Gemini when GEMINI_API_KEY is set, else Anthropic when
ANTHROPIC_API_KEY is set; DIARY_MODEL overrides the model. Only the --dry path
works without the Telegram values. Nothing here prints a secret.

Backfill: set DIARY_STATE to a file the workflow carries between runs (via cache) and DIARY_MAX_HOURS
to a per-run ceiling, and a long backlog is walked oldest-first one slice per run instead of collapsed
into a single entry; once caught up it tracks the tip normally. Unset, the diary behaves as before.

Rules the writer is held to: it says what changed and what broke, never mentions
price, the market or the token, never invents, and answers NOTHING when the window
holds only noise. Silence is the feature. Everything commit messages carry is
scrubbed of links, keys, hashes and addresses before it leaves this process.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

STEP_H = 2
WORKFLOW = "diary.yml"

VOICE = """You write the diary entry for the Telegram group of Quorum, a smart-contract scanner that reports a finding only when two independent lenses agree. Your input is raw repository activity as JSON. Your output is one short entry, or the single word NOTHING.

Rules, all of them hard:
- Plain words a non-engineer follows. Say what changed for someone using the tool, not what the code does. "The scanner now reads verified source from five chains" beats "refactored the fetch module".
- Say "we". No emoji, no hashtags, no exclamation marks, no em dashes.
- Never mention price, chart, market, buying, selling, holders, or the token. Never say the tool needs the token. Never say we won anything.
- Four states, never mixed: designed (written down), built (in the repo), tested (a test ran and passed, and the input shows it), proven. Use the weakest word the input supports. A commit that says "tests" is not proof a test passed unless a passing run is in the input.
- If something failed, broke, or was reverted, say so in plain words. Do not soften it.
- Never invent. If a commit's meaning is unclear, leave it out. Do not count, rank or order things (first, second, fourth) unless the input states the number; when it does, use that number.
- Never repeat a link, a key, a hash, a number that looks like an id, or an address, even if one appears in the input.
- A release is never noise. A change to what the tool reads, finds, reports or refuses is never noise. A new measurement is never noise. If even one item in the input is one of those, write the entry about that item and leave the noise out.
- Only if every item is noise (typos, formatting, dependency bumps, workflow config, empty merges, brand images with no change to the tool) reply with exactly: NOTHING
- Format: first line a two-to-six word headline wrapped in <b></b>. Then two to five short lines, one thing each. Then, only if there is a failure or an open problem, one line starting with "Still broken:" or "Not done yet:". Nothing else. Under 700 characters.
- Never name a person, an account, a handle or an author. The entry is by "we", about the code.
- Nothing that is not in the input: no plans, no dates, no promises, no internal file, folder, version or branch names, no wallet or contract details, no mention of keys, tokens, secrets, bots, or infrastructure.
- No hype words: thorough, comprehensive, exhaustive, battle-tested, production-ready, bulletproof, rock-solid, robust, seamless, powerful, exciting, delve, landscape, leverage, unlock, empower, journey, game-changer.
- Write like a person: varied sentence length, no lists of three for effect, no "not just X but Y", no closing line that sums up or cheers.
- Telegram HTML only: <b>, <i>, <code>. No markdown."""

BANNED = re.compile(r"\b(thorough|comprehensive|exhaustive|battle-tested|production-ready|bulletproof|rock-solid|robust|seamless|"
                    r"powerful|exciting|delve|landscape|leverage|unlock|empower|journey|game-changer|won|winner|price|chart|market cap|holders?)\b", re.I)


def unfit(text: str) -> str | None:
    """Why an entry may not be posted, or None. Anything the rules forbid that the model
    still wrote means the whole entry is dropped; silence is the safe failure."""
    if "\u2014" in text or "\u2013" in text or " -- " in text:
        return "dash"
    if re.search(r"https?://|www\.|t\.me/", text):
        return "link"
    if re.search(r"\b0x[a-fA-F0-9]{6,}\b|\b[a-fA-F0-9]{32,}\b", text):
        return "address or hash"
    if re.search(r"(^|\s)@\w+", text):
        return "handle"
    m = BANNED.search(text)
    if m:
        return f"word: {m.group(0)}"
    if len(text) > 900:
        return "too long"
    return None

SECRET = re.compile(r"\b(sk|pk|ghp|gho|ghs|github_pat|xox[abp]|AKIA)[-_A-Za-z0-9]{8,}\b")


def scrub(s: str) -> str:
    """Links, keys, hashes and addresses never reach the writer or the group."""
    s = str(s or "")
    s = re.sub(r"https?://[^\s)]+", "[link]", s)
    s = SECRET.sub("[secret]", s)
    s = re.sub(r"\b0x[a-fA-F0-9]{40,64}\b", "[address]", s)
    s = re.sub(r"\b[a-fA-F0-9]{32,}\b", "[hash]", s)
    s = re.sub(r"(api[_-]?key|token|secret|password)\s*[:=]\s*\S+", r"\1=[redacted]", s, flags=re.I)
    return s


def _get(url: str, headers: dict) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "quorum-diary", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _gh(repo: str, path: str) -> object:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _get(f"https://api.github.com/repos/{repo}{path}", headers)


def _iso(ms: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000))


def _floor(ms: int) -> int:
    step = STEP_H * 3600 * 1000
    return ms // step * step


def _cap_ms() -> int:
    """A per-run ceiling on the window (DIARY_MAX_HOURS), so a long backlog is posted oldest-first over
    several runs instead of collapsed into one entry. 0 (the default) means no ceiling."""
    return int(os.getenv("DIARY_MAX_HOURS", "0")) * 3600 * 1000


def _cursor() -> int | None:
    """Where the last run stopped, carried between runs by the workflow's cache. None when not backfilling."""
    f = os.getenv("DIARY_STATE")
    if f and os.path.exists(f):
        try:
            return _floor(int(open(f).read().strip()))
        except (ValueError, OSError):
            return None
    return None


def save_cursor(end: int) -> None:
    """Record the boundary this run reached, so the next run continues from here (backfill only)."""
    f = os.getenv("DIARY_STATE")
    if f:
        try:
            open(f, "w").write(str(end))
        except OSError:
            pass


def _since_last_success(repo: str, end: int) -> int:
    try:
        runs = _gh(repo, f"/actions/workflows/{WORKFLOW}/runs?status=success&event=schedule&per_page=1")
        prev = (runs.get("workflow_runs") or [{}])[0].get("run_started_at")
    except (urllib.error.URLError, KeyError, IndexError, ValueError):
        prev = None
    if not prev:
        return end - STEP_H * 3600 * 1000
    prev_ms = int(time.mktime(time.strptime(prev, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone) * 1000
    return _floor(prev_ms)


def window(repo: str, now_ms: int, hours: int | None) -> tuple[int, int]:
    """[start, end) in ms, end the last closed two-hour boundary. Start is, in order: the cursor a
    backfill carries between runs; a fixed --hours span; else the boundary the last successful scheduled
    run stopped at (manual runs do not count), so skipped runs are covered. DIARY_MAX_HOURS caps the span,
    so a long backlog is walked oldest-first one slice per run instead of collapsed into a single entry."""
    end = _floor(now_ms)
    cur = _cursor()
    backfilling = hours is None and cur is not None    # --hours is a manual override; it wins over the cursor
    if hours:
        start = end - hours * 3600 * 1000
    elif cur is not None:
        start = cur
    else:
        start = _since_last_success(repo, end)
    cap = _cap_ms()
    if cap and not hours and end - start > cap:    # a manual --hours override is shown in full, uncapped
        end = _floor(start + cap)
    if start >= end:                       # caught up: an empty slice when backfilling, else the last step
        return (end, end) if backfilling else (end - STEP_H * 3600 * 1000, end)
    return start, end


def changes(repo: str, start: int, end: int) -> dict:
    """Commits, merged pull requests, releases and failed workflow runs inside the window, scrubbed."""
    s, u = _iso(start), _iso(end)
    commits = [{"when": c["commit"]["author"]["date"],
                "message": scrub(c["commit"]["message"]).split("\n")[0][:160],
                "body": " ".join(scrub(c["commit"]["message"]).split("\n")[1:]).strip()[:400]}
               for c in _gh(repo, f"/commits?since={s}&until={u}&per_page=100")]
    prs = [{"title": scrub(p["title"])[:160], "body": scrub(p.get("body"))[:600]}
           for p in _gh(repo, "/pulls?state=closed&sort=updated&direction=desc&per_page=50")
           if p.get("merged_at") and s <= p["merged_at"] < u]
    releases = [{"tag": r["tag_name"], "name": scrub(r.get("name")), "body": scrub(r.get("body"))[:800], "url": r["html_url"]}
                for r in _gh(repo, "/releases?per_page=20") if r.get("published_at") and s <= r["published_at"] < u]
    failures = [{"name": r["name"], "branch": r["head_branch"], "when": r["created_at"]}
                for r in (_gh(repo, f"/actions/runs?status=failure&created=>={s}&per_page=20").get("workflow_runs") or [])
                if r["created_at"] < u and r["name"] != "diary"]
    return {"repo": repo, "since": s, "until": u, "commits": commits, "prs": prs, "releases": releases, "failures": failures}


def writer() -> tuple[str, str]:
    """Which model writes the entry: Google's free-tier Gemini if its key is set, else Anthropic."""
    if os.getenv("GEMINI_API_KEY"):
        return "gemini", os.getenv("DIARY_MODEL", "gemini-3.8-flash")
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic", os.getenv("DIARY_MODEL", "claude-sonnet-5")
    raise SystemExit("set GEMINI_API_KEY (free) or ANTHROPIC_API_KEY for the writer")


def _post(req: urllib.request.Request, tries: int = 4) -> dict:
    # A free-tier model can answer 429/500/503 on a demand spike ("usually temporary"); retry those a
    # few times with a short backoff before giving up, so one busy moment does not skip an update.
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and i < tries - 1:
                time.sleep(min(2 ** i, 8))
                continue
            raise SystemExit(f"the writer refused the request ({e.code}): {e.read().decode(errors='replace')[:300]}") from None
        except urllib.error.URLError:
            if i < tries - 1:
                time.sleep(min(2 ** i, 8))
                continue
            raise
    raise SystemExit("the writer did not answer")


def ask_gemini(model: str, system: str, user: str) -> str:
    body = json.dumps({"system_instruction": {"parts": [{"text": system}]},
                       "contents": [{"parts": [{"text": user}]}],
                       "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.4}}).encode()
    out = _post(urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body, method="POST",
        headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY", ""), "content-type": "application/json"}))
    cands = out.get("candidates") or []
    parts = (cands[0].get("content", {}).get("parts") or []) if cands else []
    return "".join(p.get("text", "") for p in parts).strip()


def ask_anthropic(model: str, system: str, user: str) -> str:
    body = json.dumps({"model": model, "max_tokens": 4000, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    out = _post(urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                headers={"x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                         "anthropic-version": "2023-06-01", "content-type": "application/json"}))
    return "".join(c.get("text", "") for c in out.get("content", [])).strip()


def write(activity: dict) -> str:
    """One entry from the writer, or NOTHING. The release links are added by code, never by the model."""
    for_model = {**activity, "releases": [{k: v for k, v in r.items() if k != "url"} for r in activity["releases"]]}
    user = "Repository activity as JSON. Write the entry or reply NOTHING.\n\n" + json.dumps(for_model)
    provider, model = writer()
    text = (ask_gemini if provider == "gemini" else ask_anthropic)(model, VOICE, user)
    if is_nothing(text):
        print(f"writer ({provider}/{model}) replied NOTHING")
        return "NOTHING"
    why = unfit(text)
    if why:
        print(f"entry dropped ({why}); nothing posted")
        return "NOTHING"
    links = "".join(f"\n{r['tag']}: {r['url']}" for r in activity["releases"])
    return text + links


def is_nothing(text: str) -> bool:
    return not text or re.fullmatch(r"\s*NOTHING\s*\.?\s*", text, flags=re.I) is not None


def send(text: str) -> None:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise SystemExit("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set")
    body = json.dumps({"chat_id": chat, "text": text[:4000], "parse_mode": "HTML", "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST",
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        out = json.loads(e.read().decode(errors="replace") or "{}")
    if not out.get("ok"):
        who = _get(f"https://api.telegram.org/bot{token}/getMe", {}).get("result", {}).get("username")
        raise SystemExit(f"telegram refused the message ({out.get('error_code')}): {out.get('description')}. "
                         f"The token belongs to @{who}; the chat is {chat}.")


def check() -> int:
    """Who the token belongs to, whether something else holds it, and whether the bot is in the chat."""
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise SystemExit("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set")
    me = _get(f"https://api.telegram.org/bot{token}/getMe", {}).get("result", {})
    hook = _get(f"https://api.telegram.org/bot{token}/getWebhookInfo", {}).get("result", {})
    print(f"token belongs to @{me.get('username')} (id {me.get('id')})")
    print("webhook: " + (f"set, to host {hook['url'].split('/')[2]}" if hook.get("url") else "none"))
    print(f"pending updates: {hook.get('pending_update_count', 0)}")
    try:
        m = _get(f"https://api.telegram.org/bot{token}/getChatMember?chat_id={chat}&user_id={me.get('id')}", {}).get("result", {})
        print(f"in the chat: {m.get('status')}")
    except urllib.error.HTTPError as e:
        print("in the chat: no (" + json.loads(e.read().decode(errors="replace") or "{}").get("description", str(e.code)) + ")")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry", action="store_true", help="print what would be posted and post nothing")
    ap.add_argument("--hours", type=int, default=None, help="widen the window back from the last closed boundary")
    ap.add_argument("--check", action="store_true", help="report the bot's state on Telegram and exit")
    a = ap.parse_args(argv)
    if a.check:
        return check()
    repo = os.getenv("GITHUB_REPO", "Yonkoo11/quorum")
    start, end = window(repo, int(time.time() * 1000), a.hours)
    activity = changes(repo, start, end)
    n = sum(len(activity[k]) for k in ("commits", "prs", "releases", "failures"))
    print(f"window {activity['since']} to {activity['until']}: {n} events")
    if a.dry:
        for k in ("commits", "prs", "releases", "failures"):
            for item in activity[k]:
                print(f"  {k[:-1]}: {item.get('message') or item.get('title') or item.get('tag') or item.get('name')}")
    advance = not a.dry and not a.hours          # a --hours override must not move the backfill cursor
    if not n:
        if advance:
            save_cursor(end)
        return 0
    text = write(activity)
    if text == "NOTHING":
        if advance:
            save_cursor(end)
        print("nothing worth saying")
        return 0
    if a.dry:
        print("--- would post ---\n" + text)
        return 0
    send(text)
    if advance:
        save_cursor(end)
    print("posted:\n" + text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
