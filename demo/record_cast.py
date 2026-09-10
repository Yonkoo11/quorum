"""Record a real pty session into an asciicast v2 file. No screen capture involved.

The child inherits the environment with every secret-shaped variable stripped, so
the recorded session can reach a read-only RPC endpoint but no signing material
is ever in scope for the commands being filmed.
"""
import json, os, time
import pexpect

COLS, ROWS = 118, 32
OUT = "demo.cast"
DENY = ("PRIVATE", "SECRET", "PASSW", "MNEMONIC", "SEED", "APIKEY", "API_KEY", "_KEY", "TOKEN")

env = {k: v for k, v in os.environ.items() if not any(d in k.upper() for d in DENY)}
env.update({"TERM": "xterm-256color", "COLUMNS": str(COLS), "LINES": str(ROWS),
            "PATH": "/Users/yonko/Projects/quorum/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": "/Users/yonko"})

child = pexpect.spawn("/bin/zsh", ["-f", "./run-demo.sh"], dimensions=(ROWS, COLS),
                      timeout=None, encoding="utf-8", codec_errors="replace", env=env)

t0 = time.time()
events = []
while True:
    try:
        chunk = child.read_nonblocking(size=65536, timeout=5)
    except pexpect.exceptions.EOF:
        break
    except pexpect.exceptions.TIMEOUT:
        if not child.isalive():
            break
        continue
    if chunk:
        events.append([round(time.time() - t0, 4), "o", chunk])

child.close()
header = {"version": 2, "width": COLS, "height": ROWS, "timestamp": int(t0),
          "env": {"TERM": "xterm-256color", "SHELL": "/bin/zsh"}}
with open(OUT, "w") as fh:
    fh.write(json.dumps(header) + "\n")
    for e in events:
        fh.write(json.dumps(e) + "\n")
print(f"recorded {len(events)} events, {events[-1][0]:.1f}s -> {OUT}")
