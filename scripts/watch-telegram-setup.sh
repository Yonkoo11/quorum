#!/bin/bash
# One-time: choose the Telegram chat the watcher and the drift check post to.
# Run: bash scripts/watch-telegram-setup.sh
# It prints a one-time code. Send that code to the Quorum buy bot from the chat you want alerts in
# (your private chat with the bot, or a group the bot is in). Only a message carrying that exact code
# is accepted, so a stranger messaging the public bot cannot become the alert chat.
# Saves the chat as QUORUM_WATCH_TG_CHAT in ~/.quorum-buybot.env; prints chat types and titles only,
# never the token or the ids. The buy bot's own announcement chat is never used for alerts.
set -euo pipefail
ENV=$HOME/.quorum-buybot.env
[ -f "$ENV" ] || { echo "missing $ENV (the buy bot's env file)" >&2; exit 1; }
source "$ENV"
: "${BUYBOT_TG_TOKEN:?no bot token in $ENV}"
api="https://api.telegram.org/bot$BUYBOT_TG_TOKEN"
code="quorum-$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"   # (tr | head on urandom dies with SIGPIPE under pipefail)

bot=$(curl -sf "$api/getMe" | python3 -c 'import sys, json; print("@" + json.load(sys.stdin)["result"]["username"])' 2>/dev/null || echo "the Quorum buy bot")
echo "Send this code to $bot from the chat you want alerts in (waiting up to 30 minutes):"
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
curl -s -X POST "$api/sendMessage" -d "chat_id=$pick" --data-urlencode "text=[Quorum watch] this chat now receives watcher alerts, heartbeats and the daily drift check." >/dev/null
echo "saved. Restarting the watchers so they pick it up:"
for a in watch-ethereum watch-arbitrum; do launchctl kickstart -k "gui/$(id -u)/com.quorum.$a" && echo "  $a restarted"; done
