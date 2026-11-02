#!/bin/bash
# One-time setup of the watcher's own Telegram bot. Run it in the Terminal app (it asks for input):
#   bash ~/Projects/quorum/scripts/watch-telegram-setup.sh
# Before running: in Telegram, message @BotFather, send /newbot, name it (e.g. "Quorum Watch"),
# and copy the token BotFather gives you. The script:
#   1. asks for that token (typed hidden) and saves it to ~/.quorum-watch.env (mode 600);
#   2. prints a one-time code; send it to the new bot from the chat you want alerts in
#      (your private chat with it, or a group you added it to). Only the chat that sends the
#      code is accepted; the bot is new and private, so nobody else is talking to it anyway;
#   3. saves that chat, sends a test line to it, and starts (or restarts) the watcher services.
# Nothing here touches the buy bot or its chat.
set -euo pipefail
ENV=$HOME/.quorum-watch.env
REPO=$(cd "$(dirname "$0")/.." && pwd)

token=""
if [ -f "$ENV" ]; then
  source "$ENV"
  token=${QUORUM_WATCH_TG_TOKEN:-}
fi
if [ -z "$token" ]; then
  read -rsp "Paste the token BotFather gave you for the watch bot (not shown): " token; echo
  [ -n "$token" ] || { echo "no token entered" >&2; exit 1; }
  umask 077
  printf 'export QUORUM_WATCH_TG_TOKEN=%s\n' "$token" > "$ENV"
  chmod 600 "$ENV"
fi
api="https://api.telegram.org/bot$token"
bot=$(curl -sf "$api/getMe" | python3 -c 'import sys, json; print("@" + json.load(sys.stdin)["result"]["username"])') \
  || { echo "Telegram rejected the token. Check it with BotFather and run again." >&2; rm -f "$ENV"; exit 1; }

code="quorum-$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"   # (tr | head on urandom dies with SIGPIPE under pipefail)
echo "Bot is $bot. Send this code to it from the chat you want alerts in (waiting up to 30 minutes):"
echo
echo "    $code"
echo
pick=""
for _ in $(seq 360); do
  pick=$(curl -sf "$api/getUpdates" | python3 -c '
import sys, json
code = sys.argv[1]
try:
    updates = json.load(sys.stdin).get("result", [])
except ValueError:
    updates = []   # empty or broken reply: try again on the next poll
for u in updates:
    m = u.get("message") or {}
    if (m.get("text") or "").strip() == code:
        c = m["chat"]
        print("watch chat:", c["type"], repr(c.get("title") or c.get("first_name") or ""), file=sys.stderr)
        print(c["id"])
        break' "$code" || true)
  [ -n "$pick" ] && break
  sleep 5
done
[ -n "$pick" ] || { echo "no message with the code arrived in 30 minutes; run the script again" >&2; exit 1; }

if /usr/bin/grep -q "^export QUORUM_WATCH_TG_CHAT=" "$ENV"; then
  sed -i '' "s/^export QUORUM_WATCH_TG_CHAT=.*/export QUORUM_WATCH_TG_CHAT=$pick/" "$ENV"
else
  echo "export QUORUM_WATCH_TG_CHAT=$pick" >> "$ENV"
fi
curl -s -X POST "$api/sendMessage" -d "chat_id=$pick" --data-urlencode "text=[Quorum watch] this chat now receives watcher alerts, hourly heartbeats and the daily drift check." >/dev/null
echo "saved. Starting the watcher services:"
for a in watch-ethereum watch-arbitrum drift; do
  plist=$HOME/Library/LaunchAgents/com.quorum.$a.plist
  if launchctl list "com.quorum.$a" >/dev/null 2>&1; then
    launchctl kickstart -k "gui/$(id -u)/com.quorum.$a" && echo "  $a restarted"
  else
    launchctl load "$plist" && echo "  $a started"
  fi
done
pkill -f "watch.live.*--dry-run" 2>/dev/null && echo "  stopped the old print-only watcher" || true
echo "done. Alerts now go to $bot's chat. Logs: $REPO/ai/watch-ethereum.out and watch-arbitrum.out"
