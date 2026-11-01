#!/bin/bash
# One-time: choose the Telegram chat the watcher and the drift check post to.
# 1. In Telegram, send the Quorum buy bot one message from the chat you want alerts in
#    (your private chat with the bot, or a group the bot is in).
# 2. Run: bash scripts/watch-telegram-setup.sh
# It saves that chat as QUORUM_WATCH_TG_CHAT in ~/.quorum-buybot.env and prints only chat types and
# titles, never the token or the ids. The buy bot's own chat is never used for alerts.
set -euo pipefail
ENV=$HOME/.quorum-buybot.env
[ -f "$ENV" ] || { echo "missing $ENV (the buy bot's env file)" >&2; exit 1; }
source "$ENV"
: "${BUYBOT_TG_TOKEN:?no bot token in $ENV}"
api="https://api.telegram.org/bot$BUYBOT_TG_TOKEN"

echo -n "buy-bot chat (announcements, NOT used for alerts): "
curl -s "$api/getChat?chat_id=${BUYBOT_TG_CHAT:-}" | python3 -c '
import sys, json
r = json.load(sys.stdin).get("result") or {}
print(r.get("type", "unknown"), repr(r.get("title") or r.get("username") or ""))'

pick=$(curl -s "$api/getUpdates" | python3 -c '
import sys, json
chats = [u["message"]["chat"] for u in json.load(sys.stdin).get("result", []) if "message" in u]
if not chats:
    sys.exit("no message found: send the bot one message from the chat you want, then rerun")
c = chats[-1]
print("watch chat:", c["type"], repr(c.get("title") or c.get("first_name") or ""), file=sys.stderr)
print(c["id"])')

if /usr/bin/grep -q "^export QUORUM_WATCH_TG_CHAT=" "$ENV"; then
  sed -i '' "s/^export QUORUM_WATCH_TG_CHAT=.*/export QUORUM_WATCH_TG_CHAT=$pick/" "$ENV"
else
  echo "export QUORUM_WATCH_TG_CHAT=$pick" >> "$ENV"
fi
curl -s -X POST "$api/sendMessage" -d "chat_id=$pick" --data-urlencode "text=[Quorum watch] this chat now receives watcher alerts, heartbeats and the daily drift check." >/dev/null
echo "saved. Restarting the watchers so they pick it up:"
for a in watch-ethereum watch-arbitrum; do launchctl kickstart -k "gui/$(id -u)/com.quorum.$a" && echo "  $a restarted"; done
