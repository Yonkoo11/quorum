#!/bin/zsh
# One-shot: set the channel, post a test, report clearly. Reads the token from your env file only.
#   bot/connect.sh @runQuorumchat
ENV=$HOME/.quorum-buybot.env
[ -f "$ENV" ] || { echo "FAIL: $ENV not found — write your token there first"; exit 1; }
source "$ENV" 2>/dev/null
[ -n "$BUYBOT_TG_TOKEN" ] || { echo "FAIL: no BUYBOT_TG_TOKEN in $ENV"; exit 1; }
CHAT="${1:-$BUYBOT_TG_CHAT}"
[ -n "$CHAT" ] || { echo "FAIL: give the channel, e.g. bot/connect.sh @runQuorumchat"; exit 1; }
# persist the chat (token line untouched)
grep -v '^export BUYBOT_TG_CHAT=' "$ENV" > "$ENV.tmp" && echo "export BUYBOT_TG_CHAT=$CHAT" >> "$ENV.tmp" && mv "$ENV.tmp" "$ENV"
echo "chat set to: $CHAT"
resp=$(curl -s "https://api.telegram.org/bot${BUYBOT_TG_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" \
  --data-urlencode "text=🟢 QUORUM buy bot connected — watching for \$50+ buys.")
echo "$resp" | /usr/bin/python3 -c "import sys,json
d=json.load(sys.stdin)
print('SUCCESS: test message posted to', d['result']['chat'].get('title') or d['result']['chat'].get('username')) if d.get('ok') else print('FAILED:', d.get('error_code'),'-', d.get('description'))" 2>/dev/null || echo "raw: $resp"
