"""Print your Telegram chat id, reading the token from the environment (never from the chat).

    source ~/.quorum-buybot.env && python bot/chat-id.py

Prints only the chat id and a plain-English reason when it can't find one. Never prints the token.
"""
import json, os, sys, urllib.request, urllib.error

tok = os.environ.get("BUYBOT_TG_TOKEN")
if not tok:
    sys.exit("BUYBOT_TG_TOKEN is not set. Run: source ~/.quorum-buybot.env  (then re-run)")

try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=15) as r:
        doc = json.load(r)
except urllib.error.HTTPError as e:
    body = json.loads(e.read() or b"{}")
    code = body.get("error_code")
    if code == 401:
        sys.exit("Telegram says the token is invalid or revoked. Make a new one in @BotFather (/token or /revoke), "
                 "rewrite ~/.quorum-buybot.env, then re-run.")
    if code == 409:
        sys.exit("A webhook is set on this bot, so getUpdates is blocked. Delete it, then re-run:\n"
                 f"  curl -s 'https://api.telegram.org/bot$BUYBOT_TG_TOKEN/deleteWebhook'")
    sys.exit(f"Telegram error {code}: {body.get('description')}")

updates = doc.get("result", [])
seen = []
for u in updates:
    chat = (u.get("channel_post") or u.get("message") or u.get("my_chat_member", {}).get("chat") and u["my_chat_member"] or {}).get("chat", {})
    if chat and chat.get("id") not in [c["id"] for c in seen]:
        seen.append(chat)

if not seen:
    print("No chats found yet. Do these, then re-run this command:")
    print("  1. Add the bot to your channel or group as an ADMIN.")
    print("  2. Post one message in that channel/group AFTER adding the bot.")
    print("  3. (If it's a private DM test instead) open the bot in Telegram and send it any message.")
    sys.exit(0)

for c in seen:
    name = c.get("title") or c.get("username") or c.get("first_name") or "?"
    print(f"chat id: {c.get('id')}   ({c.get('type')})   {name}")
