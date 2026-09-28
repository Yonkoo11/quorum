"""QUORUM buy bot: announce every on-chain buy of $50 or more.

    python bot/buybot.py --once --dry-run        # one poll, print to stdout, post nothing
    python bot/buybot.py                          # poll forever, post buys >= $50

QUORUM trades as a Uniswap v4 pool on Robinhood Chain (chain 4663), paired with native ETH. v4 has no
per-pair contract, so a buy is a `Swap` event from the PoolManager singleton filtered by this pool's id.
The event carries the swapper's balance delta: QUORUM positive means QUORUM was received, i.e. a BUY,
and the ETH spent is the size of the negative ETH leg. USD is that ETH leg times the live ETH price the
pool itself implies (DexScreener priceUsd / priceNative), so no separate price feed is trusted.

Nothing here holds a secret. Posting credentials come from the environment; without them the bot runs
in dry-run and prints. State (the last block scanned, and seen swaps) is a small JSON file so a restart
does not double-post.

Env:
  QUORUM_RPC            Robinhood Chain RPC (default the public node)
  BUYBOT_MIN_USD        threshold, default 50
  BUYBOT_TG_TOKEN       Telegram bot token   (set both to post to Telegram)
  BUYBOT_TG_CHAT        Telegram chat id
  BUYBOT_STATE          state file path (default bot/.buybot-state.json)
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

from web3 import Web3

RPC = os.environ.get("QUORUM_RPC", "https://rpc.mainnet.chain.robinhood.com")
POOL_ID = "0xc05ab314a9d7600253caf605e327b72a7dab23c63555d684ad15181d98cca3c8"
POOL_MANAGER = Web3.to_checksum_address("0x8366a39CC670B4001A1121B8F6A443A643e40951")
SWAP_TOPIC = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
TOKEN = "0xa6452Fd7134218f62056a304eaf501F8714A26b9"
DEXS = f"https://api.dexscreener.com/latest/dex/pairs/robinhood/{POOL_ID}"
UA = {"User-Agent": "Mozilla/5.0 (quorum-buybot)"}  # DexScreener blocks the default urllib agent
EXPLORER_TX = "https://robinhoodchain.blockscout.com/tx/"
DEXSCREENER = f"https://dexscreener.com/robinhood/{POOL_ID}"
MIN_USD = float(os.environ.get("BUYBOT_MIN_USD", "50"))
STATE = Path(os.environ.get("BUYBOT_STATE", Path(__file__).parent / ".buybot-state.json"))
CONFIRMATIONS = 2          # let a block settle before announcing
MAX_SPAN = 40000           # cap a single getLogs range so a long downtime backfills in chunks


def s128(word: int) -> int:
    """A signed int128 out of a 32-byte log word."""
    word &= (1 << 128) - 1
    return word - (1 << 128) if word >= (1 << 127) else word


def eth_usd() -> float | None:
    """ETH's USD price the pool itself implies, so no external feed decides the threshold."""
    try:
        with urllib.request.urlopen(urllib.request.Request(DEXS, headers=UA), timeout=15) as r:
            doc = json.load(r)
        pairs = doc.get("pairs") or ([doc["pair"]] if doc.get("pair") else [])
        p = pairs[0]
        usd, native = float(p["priceUsd"]), float(p["priceNative"])
        return usd / native if native else None
    except Exception:
        return None


def load_state(latest: int) -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"last_block": latest - 1, "seen": []}


def save_state(state: dict) -> None:
    state["seen"] = state["seen"][-500:]      # enough to dedupe across a poll boundary
    STATE.parent.mkdir(parents=True, exist_ok=True)   # a fresh host may not have the dir yet
    STATE.write_text(json.dumps(state))


def buys_in(w3: Web3, lo: int, hi: int, price: float | None) -> list[dict]:
    logs = w3.eth.get_logs({"address": POOL_MANAGER, "fromBlock": lo, "toBlock": hi,
                            "topics": [SWAP_TOPIC, POOL_ID]})
    out = []
    for lg in logs:
        raw = lg["data"]
        d = bytes(raw) if isinstance(raw, (bytes, bytearray)) else bytes.fromhex(raw[2:])
        eth_delta = s128(int.from_bytes(d[0:32], "big"))     # currency0 = native ETH (address 0 sorts first)
        quorum_delta = s128(int.from_bytes(d[32:64], "big"))  # currency1 = QUORUM
        if quorum_delta <= 0:                                 # a buy receives QUORUM; a sell does not
            continue
        eth_in = abs(eth_delta) / 1e18
        usd = eth_in * price if price else None
        out.append({"tx": lg["transactionHash"].hex(), "log": lg["logIndex"], "block": lg["blockNumber"],
                    "eth": eth_in, "quorum": quorum_delta / 1e18, "usd": usd})
    return out


def format_buy(b: dict) -> str:
    q = f"{b['quorum']:,.0f}"
    usd = f"${b['usd']:,.0f}" if b["usd"] else "$? (price feed down)"
    tx = b["tx"] if b["tx"].startswith("0x") else "0x" + b["tx"]
    return (f"\U0001F7E2 QUORUM buy  {usd}\n"
            f"{b['eth']:.4f} ETH  →  {q} QUORUM\n"
            f"tx: {EXPLORER_TX}{tx}\n"
            f"chart: {DEXSCREENER}")


def post_telegram(text: str) -> bool:
    token, chat = os.environ.get("BUYBOT_TG_TOKEN"), os.environ.get("BUYBOT_TG_CHAT")
    if not token or not chat:
        return False
    body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", body,
                                 {"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as exc:
        print(f"telegram post failed: {exc}")
        return False


def poll(w3: Web3, dry_run: bool) -> int:
    latest = w3.eth.block_number - CONFIRMATIONS
    state = load_state(latest)
    lo = state["last_block"] + 1
    if lo > latest:
        return 0
    price, posted = eth_usd(), 0
    for start in range(lo, latest + 1, MAX_SPAN):
        end = min(start + MAX_SPAN - 1, latest)
        for b in buys_in(w3, start, end, price):
            key = f"{b['tx']}:{b['log']}"
            if key in state["seen"]:
                continue
            state["seen"].append(key)
            if b["usd"] is not None and b["usd"] < MIN_USD:
                continue                                     # below threshold, but recorded so we skip it next time
            msg = format_buy(b)
            if dry_run or not post_telegram(msg):
                print(msg + ("\n(dry-run)" if dry_run else "\n(not posted: set BUYBOT_TG_TOKEN/CHAT)") + "\n")
            posted += 1
    state["last_block"] = latest
    save_state(state)
    return posted


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Announce QUORUM buys of $50+ from the v4 pool.")
    ap.add_argument("--once", action="store_true", help="one poll, then exit")
    ap.add_argument("--dry-run", action="store_true", help="print, never post")
    ap.add_argument("--interval", type=int, default=30, help="seconds between polls")
    a = ap.parse_args(argv)
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
    if w3.eth.chain_id != 4663:
        raise SystemExit(f"RPC is chain {w3.eth.chain_id}, not Robinhood Chain (4663)")
    print(f"buybot: pool {POOL_ID[:10]}… threshold ${MIN_USD:.0f} "
          f"{'DRY-RUN' if a.dry_run else 'posting to Telegram' if os.environ.get('BUYBOT_TG_TOKEN') else 'no channel set (prints)'}")
    while True:
        try:
            n = poll(w3, a.dry_run)
            if a.once:
                print(f"done: {n} buy(s) at or above threshold")
                return
        except Exception as exc:
            print(f"poll error (will retry): {exc}")
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
